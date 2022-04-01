import json
import logging

import requests
from django.http import JsonResponse, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt

from boogie_api.models import Player, Song

logger = logging.getLogger("django.server.dupa")  # TODO
groovestats_proxy_enabled = False  # TODO take from settings?
GROOVESTATS_ENDPOINT = "https://api.groovestats.com"  # TODO take from settings?
GROOVESTATS_RESPONSES = {
    "MISSING_CHARTS": {
        "message": "Something went wrong.",
        "error": "Required query parameter 'chartHashP1' or 'chartHashP2' not found.",
    },
    "MISSING_API_KEYS": {
        "message": "Something went wrong.",
        "error": "Header 'x-api-key-player-1' or 'x-api-key-player-2' not found.",
    },
    "NEW_SESSION": {
        "activeEvents": [{"name":"ITL 2022","shortName":"ITL2022","url":"https:\/\/itl2022.groovestats.com"}],
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


def player_scores(request):
    has_p1 = has_p2 = False
    leaderboard1 = []
    leaderboard2 = []
    params = {}
    headers = {}

    hash_p1 = request.GET.get("chartHashP1")
    hash_p2 = request.GET.get("chartHashP2")
    api_key_p1 = request.headers.get("x-api-key-player-1")
    api_key_p2 = request.headers.get("x-api-key-player-2")

    if not (hash_p1 or hash_p2):
        return JsonResponse(data=GROOVESTATS_RESPONSES["MISSING_CHARTS"])

    if not (api_key_p1 or api_key_p2):
        return JsonResponse(data=GROOVESTATS_RESPONSES["MISSING_API_KEYS"])

    if hash_p1 and api_key_p1:
        has_p1 = True
        p1 = Player.get_by_gs_api_key(api_key_p1)  # TODO might not exist? Create at first submission?
        song1 = Song.objects.filter(hash=hash_p1).first()

        if song1:
            leaderboard1 = song1.get_leaderboard(num_entries=1, player=p1)
        else:
            params["chartHashP1"] = hash_p1
            headers["x-api-key-player-1"] = api_key_p1

    if hash_p2 and api_key_p2:
        has_p2 = True
        p2 = Player.get_by_gs_api_key(api_key_p2)
        song2 = Song.objects.filter(hash=hash_p2).first()

        if song2:
            leaderboard2 = song2.get_leaderboard(num_entries=1, player=p2)
        else:
            params["chartHashP2"] = hash_p2
            headers["x-api-key-player-2"] = api_key_p2

    if params and headers:
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

    if has_p1:
        if leaderboard1:
            final_response["player1"] = {
                "chartHash": hash_p1,
                "isRanked": True,
                "gsLeaderboard": leaderboard1,
            }
        elif gs_response:
            final_response["player1"] = {
                "chartHash": hash_p1,
                "isRanked": True,
                "gsLeaderboard": gs_response.get("player1", {}).get("gsLeaderboard", []),
            }
            if p1_itl := gs_response.get("player1", {}).get("itl"):
                final_response["player1"]["itl"] = p1_itl
        else:
            final_response["player1"] = {
                "chartHash": hash_p1,
                "isRanked": True,
                "gsLeaderboard": [],
            }

    if has_p2:
        if leaderboard2:
            final_response["player2"] = {
                "chartHash": hash_p2,
                "isRanked": True,
                "gsLeaderboard": leaderboard2,
            }
        elif gs_response:
            final_response["player2"] = {
                "chartHash": hash_p2,
                "isRanked": True,
                "gsLeaderboard": gs_response.get("player2", {}).get("gsLeaderboard", []),
            }
            if p2_itl := gs_response.get("player2", {}).get("itl"):
                final_response["player2"]["itl"] = p2_itl
        else:
            final_response["player2"] = {
                "chartHash": hash_p2,
                "isRanked": True,
                "gsLeaderboard": [],
            }

    return JsonResponse(data=final_response)


def player_leaderboards(request):
    has_p1 = has_p2 = False
    leaderboard1 = []
    leaderboard2 = []
    params = {}
    headers = {}

    hash_p1 = request.GET.get("chartHashP1")
    hash_p2 = request.GET.get("chartHashP2")
    api_key_p1 = request.headers.get("x-api-key-player-1")
    api_key_p2 = request.headers.get("x-api-key-player-2")
    max_results = int(request.GET.get("maxLeaderboardResults", 0))

    if not max_results:
        return JsonResponse(data=GROOVESTATS_RESPONSES["MISSING_LEADERBOARDS_LIMIT"])
    params["maxLeaderboardResults"] = max_results

    if not (hash_p1 or hash_p2):
        return JsonResponse(data=GROOVESTATS_RESPONSES["MISSING_CHARTS"])

    if not (api_key_p1 or api_key_p2):
        return JsonResponse(data=GROOVESTATS_RESPONSES["MISSING_API_KEYS"])

    if hash_p1 and api_key_p1:
        has_p1 = True
        p1 = Player.get_by_gs_api_key(api_key_p1)
        song1 = Song.objects.filter(hash=hash_p1).first()

        if song1:
            leaderboard1 = song1.get_leaderboard(num_entries=max_results, player=p1)
        else:
            params["chartHashP1"] = hash_p1
            headers["x-api-key-player-1"] = api_key_p1

    if hash_p2 and api_key_p2:
        has_p2 = True
        p2 = Player.get_by_gs_api_key(api_key_p2)
        song2 = Song.objects.filter(hash=hash_p2).first()

        if song2:
            leaderboard2 = song2.get_leaderboard(num_entries=max_results, player=p2)
        else:
            params["chartHashP2"] = hash_p2
            headers["x-api-key-player-2"] = api_key_p2

    if params and headers:
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

    if has_p1:
        if leaderboard1:
            final_response["player1"] = {
                "chartHash": hash_p1,
                "isRanked": True,
                "gsLeaderboard": leaderboard1,
            }
        elif gs_response:
            final_response["player1"] = {
                "chartHash": hash_p1,
                "isRanked": True,
                "gsLeaderboard": gs_response.get("player1", {}).get("gsLeaderboard", []),
            }
            if p1_itl := gs_response.get("player1", {}).get("itl"):
                final_response["player1"]["itl"] = p1_itl
        else:
            final_response["player1"] = {
                "chartHash": hash_p1,
                "isRanked": True,
                "gsLeaderboard": [],
            }

    if has_p2:
        if leaderboard2:
            final_response["player2"] = {
                "chartHash": hash_p2,
                "isRanked": True,
                "gsLeaderboard": leaderboard2,
            }
        elif gs_response:
            final_response["player2"] = {
                "chartHash": hash_p2,
                "isRanked": True,
                "gsLeaderboard": gs_response.get("player2", {}).get("gsLeaderboard", []),
            }
            if p2_itl := gs_response.get("player2", {}).get("itl"):
                final_response["player2"]["itl"] = p2_itl
        else:
            final_response["player2"] = {
                "chartHash": hash_p2,
                "isRanked": True,
                "gsLeaderboard": [],
            }

    return JsonResponse(data=final_response)


@csrf_exempt
def score_submit(request):
    has_p1 = has_p2 = False
    leaderboard1 = []
    leaderboard2 = []
    params = {}
    headers = {}

    hash_p1 = request.GET.get("chartHashP1")
    hash_p2 = request.GET.get("chartHashP2")
    api_key_p1 = request.headers.get("x-api-key-player-1")
    api_key_p2 = request.headers.get("x-api-key-player-2")
    max_results = int(request.GET.get("maxLeaderboardResults", 0))

    if not max_results:
        return JsonResponse(data=GROOVESTATS_RESPONSES["MISSING_LEADERBOARDS_LIMIT"])
    params["maxLeaderboardResults"] = max_results

    if not (hash_p1 or hash_p2):
        return JsonResponse(data=GROOVESTATS_RESPONSES["MISSING_CHARTS"])

    if not (api_key_p1 or api_key_p2):
        return JsonResponse(data=GROOVESTATS_RESPONSES["MISSING_API_KEYS"])

    try:
        body_parsed = json.loads(request.body)
    except json.JSONDecodeError:
        # TODO early exit?
        body_parsed = {}

    if hash_p1 and api_key_p1 and body_parsed.get("player1") is not None:
        has_p1 = True
        params["chartHashP1"] = hash_p1
        headers["x-api-key-player-1"] = api_key_p1

    if hash_p2 and api_key_p2 and body_parsed.get("player2") is not None:
        has_p2 = True
        params["chartHashP2"] = hash_p2
        headers["x-api-key-player-2"] = api_key_p2

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

    if has_p1:
        p1_ranked = gs_response["player1"]["isRanked"]
        p1_itl = None

        if p1_ranked:
            leaderboard1 = gs_response["player1"]["gsLeaderboard"]
            p1_result = gs_response["player1"]["result"]
            p1_delta = gs_response["player1"]["scoreDelta"]
            if "itl" in gs_response["player1"]:
                p1_itl = gs_response["player1"]["itl"]
        else:
            song1, song_created = Song.objects.get_or_create(hash=hash_p1)

            p1 = Player.get_by_gs_api_key(api_key_p1)

            if not p1:
                bs_api_key = Player.gs_api_key_to_bs_api_key(api_key_p1)
                p1 = Player.objects.create(api_key=bs_api_key, machine_tag=bs_api_key[:4])  # TODO

            _, old_score = song1.get_highscore(p1)
            if old_score:
                if old_score.score < body_parsed["player1"]["score"]:
                    p1_result = "improved"
                else:
                    p1_result = "score-not-improved"

                p1_delta = body_parsed["player1"]["score"] - old_score.score
            else:
                p1_result = "score-added"
                p1_delta = body_parsed["player1"]["score"]

            p1.scores.create(
                song=song1,
                score=body_parsed["player1"]["score"],
                comment=body_parsed["player1"]["comment"],
                profile_name=None,
            )

            leaderboard1 = song1.get_leaderboard(num_entries=max_results, player=p1)

    if has_p2:
        p2_ranked = gs_response["player2"]["isRanked"]
        p2_itl = None

        if p2_ranked:
            leaderboard2 = gs_response["player2"]["gsLeaderboard"]
            p2_result = gs_response["player2"]["result"]
            p2_delta = gs_response["player2"]["scoreDelta"]
            if "itl" in gs_response["player2"]:
                p2_itl = gs_response["player2"]["itl"]
        else:
            song2, song_created = Song.objects.get_or_create(hash=hash_p2)

            p2 = Player.get_by_gs_api_key(api_key_p2)

            if not p2:
                bs_api_key = Player.gs_api_key_to_bs_api_key(api_key_p2)
                p2 = Player.objects.create(api_key=bs_api_key, machine_tag=bs_api_key[:4])

            _, old_score = song2.get_highscore(p2)
            if old_score:
                if old_score.score < body_parsed["player2"]["score"]:
                    p2_result = "improved"
                else:
                    p2_result = "score-not-improved"

                p2_delta = body_parsed["player2"]["score"] - old_score.score
            else:
                p2_result = "score-added"
                p2_delta = body_parsed["player2"]["score"]

            p2.scores.create(
                song=song2,
                score=body_parsed["player2"]["score"],
                comment=body_parsed["player2"]["comment"],
                profile_name=None,
            )

            leaderboard2 = song2.get_leaderboard(num_entries=max_results, player=p2)

    final_response = {}
    if has_p1:
        final_response["player1"] = {
            "chartHash": hash_p1,
            "isRanked": True,
            "gsLeaderboard": leaderboard1,
            "scoreDelta": p1_delta,
            "result": p1_result,
        }
        if p1_itl:
            final_response["player1"]["itl"] = p1_itl

    if has_p2:
        final_response["player2"] = {
            "chartHash": hash_p2,
            "isRanked": True,
            "gsLeaderboard": leaderboard2,
            "scoreDelta": p2_delta,
            "result": p2_result,
        }
        if p2_itl:
            final_response["player2"]["itl"] = p2_itl

    return JsonResponse(data=final_response)
