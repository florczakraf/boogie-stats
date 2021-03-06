import json
import logging
import uuid
from collections import defaultdict

import requests
from django.http import JsonResponse, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt

from boogiestats import __version__ as boogiestats_version
from boogiestats.boogie_api.models import Player, Song

logger = logging.getLogger("django.server.dupa")  # TODO
groovestats_proxy_enabled = False  # TODO take from settings?
GROOVESTATS_ENDPOINT = "https://api.groovestats.com"  # TODO take from settings?
GROOVESTATS_RESPONSES = {
    "PLAYERS_VALIDATION_ERROR": {
        "message": "Something went wrong.",
        "error": "No valid players found.",
    },
    "NEW_SESSION": {
        "activeEvents": [
            {
                "name": "ITL 2022",
                "shortName": "ITL2022",
                "url": r"https:\/\/itl2022.groovestats.com",
            }
        ],
        "servicesResult": "OK",
        "servicesAllowed": {
            "scoreSubmit": True,
            "playerScores": True,
            "playerLeaderboards": True,
        },
    },
    "MISSING_LEADERBOARDS_LIMIT": {
        "message": "Something went wrong.",  # TODO test this with real groovestats perhaps?
        "error": "maxLeaderboardResults parameter has not been set.",
    },
    "GROOVESTATS_DEAD": {
        "message": "Something went wrong.",
        "error": "Couldn't contact GrooveStats API.",
    },
}
GROOVESTATS_TIMEOUT = 12


def new_session(request):  # TODO add proxying to groovestats / caching?
    return JsonResponse(data=GROOVESTATS_RESPONSES["NEW_SESSION"])


def validate_players(players):
    for player_id, player in players.items():
        chart_hash = player.get("chartHash")
        gs_api_key = player.get("gsApiKey")

        if not all((chart_hash, gs_api_key)):
            raise ValueError(f"{player_id} is not valid.")


def parse_players(request):
    players = defaultdict(dict)

    for k, v in request.GET.items():
        if k.startswith("chartHashP"):
            player_index = int(k.removeprefix("chartHashP"))
            players[player_index]["chartHash"] = v

    for k, v in request.headers.items():
        if k.lower().startswith("x-api-key-player-"):
            player_index = int(k.lower().removeprefix("x-api-key-player-"))
            players[player_index]["gsApiKey"] = v

    validate_players(players)

    return players


def create_headers(request):
    return {
        "User-Agent": f"{request.headers.get('User-Agent', 'Anonymous')} via BoogieStats/{boogiestats_version}",
    }


def player_scores(request):
    params = {}
    headers = create_headers(request)
    make_request = False

    try:
        players = parse_players(request)
    except ValueError:
        return JsonResponse(data=GROOVESTATS_RESPONSES["PLAYERS_VALIDATION_ERROR"])

    for player_index, player in players.items():
        gs_api_key = player["gsApiKey"]
        chart_hash = player["chartHash"]
        player_instance = Player.get_by_gs_api_key(gs_api_key)
        song = Song.objects.filter(hash=chart_hash).first()

        if song:
            player["leaderboard"] = song.get_leaderboard(num_entries=1, player=player_instance)
        else:
            params[f"chartHashP{player_index}"] = chart_hash
            headers[f"x-api-key-player-{player_index}"] = gs_api_key
            make_request = True

    if make_request:
        try:
            gs_response = requests.get(
                GROOVESTATS_ENDPOINT + "/player-scores.php",
                params=params,
                headers=headers,
                timeout=GROOVESTATS_TIMEOUT,
            ).json()
        except requests.Timeout as e:
            logger.error(f"Request to GrooveStats timed-out: {e}")
            return HttpResponseServerError()

        logger.info(gs_response)
    else:
        gs_response = {}

    final_response = {}

    for player_index, player in players.items():
        chart_hash = player["chartHash"]
        player_id = f"player{player_index}"

        final_response[player_id] = {
            "chartHash": chart_hash,
            "isRanked": True,
        }

        if player.get("leaderboard"):
            leaderboard = player["leaderboard"]
        elif gs_response:
            leaderboard = gs_response.get(f"player{player_index}", {}).get("gsLeaderboard", [])
            player["itl"] = gs_response.get(player_id, {}).get("itl")
            if player["itl"]:
                final_response[player_id]["itl"] = player["itl"]
        else:
            leaderboard = []

        final_response[player_id]["gsLeaderboard"] = leaderboard

    return JsonResponse(data=final_response)


def player_leaderboards(request):
    params = {}
    headers = create_headers(request)
    make_request = False

    try:
        players = parse_players(request)
    except ValueError:
        return JsonResponse(data=GROOVESTATS_RESPONSES["PLAYERS_VALIDATION_ERROR"])

    max_results = int(request.GET.get("maxLeaderboardResults", 0))

    if not max_results:
        return JsonResponse(data=GROOVESTATS_RESPONSES["MISSING_LEADERBOARDS_LIMIT"])
    params["maxLeaderboardResults"] = max_results

    for player_index, player in players.items():
        gs_api_key = player["gsApiKey"]
        chart_hash = player["chartHash"]
        player_instance = Player.get_by_gs_api_key(gs_api_key)
        song = Song.objects.filter(hash=chart_hash).first()

        if song:
            player["leaderboard"] = song.get_leaderboard(num_entries=max_results, player=player_instance)
        else:
            params[f"chartHashP{player_index}"] = chart_hash
            headers[f"x-api-key-player-{player_index}"] = gs_api_key
            make_request = True

    if make_request:
        try:
            gs_response = requests.get(
                GROOVESTATS_ENDPOINT + "/player-leaderboards.php",
                params=params,
                headers=headers,
                timeout=GROOVESTATS_TIMEOUT,
            ).json()
        except requests.Timeout as e:
            logger.error(f"Request to GrooveStats timed-out: {e}")
            return HttpResponseServerError()
        logger.info(gs_response)
    else:
        gs_response = {}

    final_response = {}

    for player_index, player in players.items():
        chart_hash = player["chartHash"]
        player_id = f"player{player_index}"

        final_response[player_id] = {
            "chartHash": chart_hash,
            "isRanked": True,
        }

        if player.get("leaderboard"):
            leaderboard = player["leaderboard"]
        elif gs_response:
            leaderboard = gs_response.get(f"player{player_index}", {}).get("gsLeaderboard", [])
            player["itl"] = gs_response.get(player_id, {}).get("itl")
            if player["itl"]:
                final_response[player_id]["itl"] = player["itl"]
        else:
            leaderboard = []

        final_response[player_id]["gsLeaderboard"] = leaderboard

    return JsonResponse(data=final_response)


@csrf_exempt
def score_submit(request):
    params = {}
    headers = create_headers(request)

    try:
        players = parse_players(request)
    except ValueError:
        return JsonResponse(data=GROOVESTATS_RESPONSES["PLAYERS_VALIDATION_ERROR"])

    max_results = int(request.GET.get("maxLeaderboardResults", 0))

    if not max_results:
        return JsonResponse(data=GROOVESTATS_RESPONSES["MISSING_LEADERBOARDS_LIMIT"])
    params["maxLeaderboardResults"] = max_results

    try:
        body_parsed = json.loads(request.body)
    except json.JSONDecodeError:
        # TODO early exit?
        body_parsed = {}

    for player_index, player in players.items():
        gs_api_key = player["gsApiKey"]
        chart_hash = player["chartHash"]

        params[f"chartHashP{player_index}"] = chart_hash
        headers[f"x-api-key-player-{player_index}"] = gs_api_key

    if params and headers and body_parsed:
        try:
            gs_response = requests.post(
                GROOVESTATS_ENDPOINT + "/score-submit.php",
                params=params,
                headers=headers,
                json=body_parsed,
                timeout=GROOVESTATS_TIMEOUT,
            ).json()
        except requests.Timeout as e:
            logger.error(f"Request to GrooveStats timed-out: {e}")
            return HttpResponseServerError()
        logger.info(gs_response)
    else:
        return JsonResponse(GROOVESTATS_RESPONSES["GROOVESTATS_DEAD"])

    for player_index, player in players.items():
        player_id = f"player{player_index}"
        chart_hash = player["chartHash"]
        gs_api_key = player["gsApiKey"]
        is_ranked = gs_response.get(player_id, {}).get("isRanked", False)

        if is_ranked:
            player_response = gs_response[player_id]
            player["leaderboard"] = player_response["gsLeaderboard"]
            player["result"] = player_response["result"]
            player["delta"] = player_response["scoreDelta"]
            if "itl" in player_response:
                player["itl"] = player_response["itl"]
        else:
            song, song_created = Song.objects.get_or_create(hash=chart_hash)

            player_instance = Player.get_by_gs_api_key(gs_api_key)

            if not player_instance:
                machine_tag = uuid.uuid4().hex[:4].upper()
                player_instance = Player.objects.create(gs_api_key=gs_api_key, machine_tag=machine_tag)

            _, old_score = song.get_highscore(player_instance)
            if old_score:
                if old_score.score < body_parsed[player_id]["score"]:
                    player["result"] = "improved"
                else:
                    player["result"] = "score-not-improved"

                player["delta"] = body_parsed[player_id]["score"] - old_score.score
            else:
                player["result"] = "score-added"
                player["delta"] = body_parsed[player_id]["score"]

            player_instance.scores.create(
                song=song,
                score=body_parsed[player_id]["score"],
                comment=body_parsed[player_id]["comment"],
                profile_name=None,
            )

            player["leaderboard"] = song.get_leaderboard(num_entries=max_results, player=player_instance)

    final_response = {}

    for player_index, player in players.items():
        final_response[f"player{player_index}"] = {
            "chartHash": player["chartHash"],
            "isRanked": True,
            "gsLeaderboard": player["leaderboard"],
            "scoreDelta": player["delta"],
            "result": player["result"],
        }
        if player.get("itl"):
            final_response[f"player{player_index}"]["itl"] = player["itl"]

    return JsonResponse(data=final_response)
