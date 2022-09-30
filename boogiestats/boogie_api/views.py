import json
import logging
import uuid
from collections import defaultdict

import requests
from django.http import JsonResponse, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt

from boogiestats import __version__ as boogiestats_version
from boogiestats.boogie_api.models import Player, Song

logger = logging.getLogger("django.server.boogiestats")
GROOVESTATS_ENDPOINT = "https://api.groovestats.com"  # TODO take from settings?
GROOVESTATS_RESPONSES = {
    "PLAYERS_VALIDATION_ERROR": {
        "message": "Something went wrong.",
        "error": "No valid players found.",
    },
    "NEW_SESSION": {
        "activeEvents": [
            {
                "name": "Stamina RPG 6",
                "shortName": "SRPG6",
                "url": r"https:\/\/srpg6.groovestats.com",
            },
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

        params[f"chartHashP{player_index}"] = chart_hash
        headers[f"x-api-key-player-{player_index}"] = gs_api_key

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

    final_response = {}

    for player_index, player in players.items():
        chart_hash = player["chartHash"]
        player_id = f"player{player_index}"

        final_response[player_id] = {
            "chartHash": chart_hash,
            "isRanked": True,
        }

        gs_leaderboard = gs_response.get(f"player{player_index}", {}).get("gsLeaderboard", [])
        leaderboard = gs_leaderboard or player.get("leaderboard", [])

        final_response[player_id]["gsLeaderboard"] = leaderboard

        player["itl"] = gs_response.get(player_id, {}).get("itl")
        if player["itl"]:
            final_response[player_id]["itl"] = player["itl"]

        player["rpg"] = gs_response.get(player_id, {}).get("rpg")
        if player["rpg"]:
            final_response[player_id]["rpg"] = player["rpg"]

    return JsonResponse(data=final_response)


def player_leaderboards(request):
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

    for player_index, player in players.items():
        gs_api_key = player["gsApiKey"]
        chart_hash = player["chartHash"]
        player_instance = Player.get_by_gs_api_key(gs_api_key)
        song = Song.objects.filter(hash=chart_hash).first()

        if song:
            player["leaderboard"] = song.get_leaderboard(num_entries=max_results, player=player_instance)

        params[f"chartHashP{player_index}"] = chart_hash
        headers[f"x-api-key-player-{player_index}"] = gs_api_key

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

    final_response = {}

    for player_index, player in players.items():
        chart_hash = player["chartHash"]
        player_id = f"player{player_index}"

        final_response[player_id] = {
            "chartHash": chart_hash,
            "isRanked": True,
        }

        gs_leaderboard = gs_response.get(f"player{player_index}", {}).get("gsLeaderboard", [])
        leaderboard = gs_leaderboard or player.get("leaderboard", [])

        final_response[player_id]["gsLeaderboard"] = leaderboard

        player["itl"] = gs_response.get(player_id, {}).get("itl")
        if player["itl"]:
            final_response[player_id]["itl"] = player["itl"]

        player["rpg"] = gs_response.get(player_id, {}).get("rpg")
        if player["rpg"]:
            final_response[player_id]["rpg"] = player["rpg"]

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

        song, song_created = Song.objects.get_or_create(hash=chart_hash)
        player["song"] = song
        player["is_ranked"] = is_ranked

        player_instance = Player.get_by_gs_api_key(gs_api_key)

        if not player_instance:
            machine_tag = uuid.uuid4().hex[:4].upper()
            player_instance = Player.objects.create(gs_api_key=gs_api_key, machine_tag=machine_tag)

        player["player_instance"] = player_instance

        _, old_score = song.get_highscore(player_instance)

        comment = body_parsed[player_id].get("comment", "")
        used_cmod = body_parsed[player_id].get("usedCmod", None)
        judgments = body_parsed[player_id].get("judgmentCounts", None)

        player_instance.scores.create(
            song=song,
            score=body_parsed[player_id]["score"],
            comment=comment,
            rate=body_parsed[player_id].get("rate", 100),
            used_cmod=used_cmod,
            judgments=judgments,
        )

        player_response = gs_response.get(player_id, {})

        # event structures can be present even when song is not ranked, so we just pass them when present
        if "itl" in player_response:
            player["itl"] = player_response["itl"]

        if "rpg" in player_response:
            player["rpg"] = player_response["rpg"]

        if is_ranked:
            player["leaderboard"] = player_response["gsLeaderboard"]
            player["result"] = player_response["result"]
            player["delta"] = player_response["scoreDelta"]

            if not song.gs_ranked:
                song.gs_ranked = True
                song.save()
        else:
            if old_score:
                if old_score.score < body_parsed[player_id]["score"]:
                    player["result"] = "improved"
                else:
                    player["result"] = "score-not-improved"

                player["delta"] = body_parsed[player_id]["score"] - old_score.score
            else:
                player["result"] = "score-added"
                player["delta"] = body_parsed[player_id]["score"]

    for player in players.values():
        if not player["is_ranked"]:
            player["leaderboard"] = player["song"].get_leaderboard(
                num_entries=max_results, player=player["player_instance"]
            )

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

        if player.get("rpg"):
            final_response[f"player{player_index}"]["rpg"] = player["rpg"]

    return JsonResponse(data=final_response)
