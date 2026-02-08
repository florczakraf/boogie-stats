import json
import logging
import uuid
from collections import defaultdict
from copy import deepcopy
from typing import Optional

import requests
import sentry_sdk
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from prometheus_client import Counter

from boogiestats import __version__ as boogiestats_version
from boogiestats.boogie_api.choices import GSIntegration, GSStatus, LeaderboardSource
from boogiestats.boogie_api.models import Player, Song
from boogiestats.boogie_api.utils import set_sentry_user

logger = logging.getLogger("django.server.boogiestats")
GROOVESTATS_RESPONSES = {
    "PLAYERS_VALIDATION_ERROR": {
        "message": "Something went wrong.",
        "error": "No valid players found.",
    },
    "NEW_SESSION": {
        "activeEvents": [],
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
GROOVESTATS_TIMEOUT = (5, 20)  # (connect, read) timeout
SUPPORTED_EVENTS = ("rpg", "itl")
LB_SOURCE_MAPPING = {
    LeaderboardSource.BS.value: "BS",
    LeaderboardSource.GS.value: "GS",
}

GS_GET_REQUESTS_TOTAL = Counter("boogiestats_gs_get_requests_total", "Number of GS GET requests")
GS_GET_REQUESTS_ERRORS_TOTAL = Counter(
    "boogiestats_gs_get_requests_errors_total", "Number of unsuccessful GS GET requests"
)
GS_POST_REQUESTS_TOTAL = Counter("boogiestats_gs_post_requests_total", "Number of GS POST requests")
GS_POST_REQUESTS_ERRORS_TOTAL = Counter(
    "boogiestats_gs_post_requests_errors_total", "Number of unsuccessful GS POST requests"
)


def new_session(request):
    gs_response = _try_gs_get(request)
    response = deepcopy(GROOVESTATS_RESPONSES["NEW_SESSION"])
    response["activeEvents"] = gs_response.get("activeEvents", [])

    return JsonResponse(data=response)


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
            player_instance: Optional[Player] = Player.get_by_gs_api_key(v)
            players[player_index]["player_instance"] = player_instance
            set_sentry_user(request, player_instance)

    validate_players(players)

    return players


def create_headers(request):
    """
    Creates headers to be used when passing requests to GS.

    Some headers have to be filtered out (e.g. `Host`), otherwise GS front rejects the request.
    It's enough to just keep API keys. We also add BoogieStats to User-Agent in case GS ever decides to make usage stats.
    """

    return {
        **{k: v for k, v in request.headers.items() if k.lower().startswith("x-api-key")},
        "User-Agent": f"{request.headers.get('User-Agent', 'Anonymous')} via BoogieStats/{boogiestats_version}",
    }


def fill_event_leaderboards(final_response, gs_player, player_id):
    for event in SUPPORTED_EVENTS:
        if event_leaderboard := gs_player.get(event):
            final_response[player_id][event] = event_leaderboard


def handle_score_results(player, old_score, new_score):
    new_score_value = new_score.itg_score

    if old_score:
        old_score_value = old_score.itg_score

        if old_score_value < new_score_value:
            player["result"] = "improved"
        else:
            player["result"] = "score-not-improved"

        player["delta"] = new_score_value - old_score_value
    else:
        player["result"] = "score-added"
        player["delta"] = new_score_value


def get_local_leaderboard(player_instance, chart_hash, num_entries, score_type):
    song = Song.objects.filter(hash=chart_hash).first()

    if song:
        return song.get_leaderboard(num_entries=num_entries, score_type=score_type, player=player_instance)
    return []


def get_or_create_player(gs_api_key):
    player_instance = Player.get_by_gs_api_key(gs_api_key)
    if not player_instance:
        machine_tag = uuid.uuid4().hex[:4].upper()
        player_instance = Player.objects.create(gs_api_key=gs_api_key, machine_tag=machine_tag)
    return player_instance


def _request_leaderboards(request):
    try:
        players = parse_players(request)
    except ValueError as e:
        sentry_sdk.capture_exception(e)
        return JsonResponse(data=GROOVESTATS_RESPONSES["PLAYERS_VALIDATION_ERROR"], status=400)

    player_instances = [p["player_instance"] for p in players.values()]
    gs_integrations = [p and p.gs_integration or GSIntegration.REQUIRE for p in player_instances]
    should_attempt_gs = any(g != GSIntegration.SKIP for g in gs_integrations)

    if should_attempt_gs:
        gs_response = _try_gs_get(request)
    else:
        gs_response = {}

    final_response = {}
    response_headers = {}

    for player_index, player in players.items():
        chart_hash = player["chartHash"]
        player_id = f"player{player_index}"

        gs_player = gs_response.get(player_id, {})
        max_results = int(request.GET.get("maxLeaderboardResults", 1))

        player_instance: Optional[Player] = player["player_instance"]
        leaderboard_source = (
            player_instance.leaderboard_source if player_instance is not None else LeaderboardSource.BS.value
        )

        if leaderboard_source == LeaderboardSource.BS or not gs_player:
            final_response[player_id] = {
                "chartHash": chart_hash,
                "isRanked": True,
                "gsLeaderboard": get_local_leaderboard(player_instance, chart_hash, max_results, score_type="itg"),
                "exLeaderboard": get_local_leaderboard(player_instance, chart_hash, max_results, score_type="ex"),
            }
            fill_event_leaderboards(final_response, gs_player, player_id)

        elif leaderboard_source == LeaderboardSource.GS.value:
            final_response[player_id] = gs_player

        response_headers[f"bs-leaderboard-player-{player_index}"] = LB_SOURCE_MAPPING[leaderboard_source]

    return JsonResponse(data=final_response, headers=response_headers)


def _try_gs_get(request):
    GS_GET_REQUESTS_TOTAL.inc()
    headers = create_headers(request)
    try:
        raw_response = requests.get(
            settings.BS_UPSTREAM_API_ENDPOINT + request.path,
            params=request.GET,
            headers=headers,
            timeout=GROOVESTATS_TIMEOUT,
        )
        gs_response = raw_response.json()
        logger.info(gs_response)
    except (requests.Timeout, requests.ConnectionError):
        GS_GET_REQUESTS_ERRORS_TOTAL.inc()
        # We don't forward these events to sentry because of repeating floods.
        # Grafana or other monitoring can be used instead.

        # we can serve a local leaderboard instead of an error
        gs_response = {}
    except json.JSONDecodeError as e:
        GS_GET_REQUESTS_ERRORS_TOTAL.inc()
        sentry_sdk.set_context("GS", {"raw_response": raw_response.content, "status": raw_response.status_code})
        sentry_sdk.capture_exception(e)

        # we can serve a local leaderboard instead of an error
        gs_response = {}
    except Exception:  # catchall for incrementing metrics; reraise to let sentry catch it as an unhandled exception
        GS_GET_REQUESTS_ERRORS_TOTAL.inc()
        raise

    return gs_response


def player_scores(request):
    return _request_leaderboards(request)


def player_leaderboards(request):
    return _request_leaderboards(request)


def _make_score_submit_response(gs_response, players, max_results):
    final_response = {}
    response_headers = {}

    for player_index, player in players.items():
        player_id = f"player{player_index}"
        gs_player = gs_response.get(player_id, {})

        player_instance: Player = player["player_instance"]
        leaderboard_source = player_instance.leaderboard_source

        if leaderboard_source == LeaderboardSource.BS or not gs_player:
            final_response[player_id] = {
                "chartHash": player["chartHash"],
                "isRanked": True,
                "gsLeaderboard": get_local_leaderboard(player_instance, player["chartHash"], max_results, "itg"),
                "exLeaderboard": get_local_leaderboard(player_instance, player["chartHash"], max_results, "ex"),
                "scoreDelta": player["delta"],
                "result": player["result"],
            }
            fill_event_leaderboards(final_response, gs_player, player_id)
        elif leaderboard_source == LeaderboardSource.GS.value:
            final_response[player_id] = gs_player  # isRanked might be False /shrug
        else:
            raise ValueError(
                f"unknown leaderboard source {player_instance.leaderboard_source} for player #{player_id} {player}"
            )

        response_headers[f"bs-leaderboard-player-{player_index}"] = LB_SOURCE_MAPPING[leaderboard_source]

    return final_response, response_headers


def _post_gs(request, body_parsed, require_gs):
    headers = create_headers(request)
    gs_response = {}

    try:
        GS_POST_REQUESTS_TOTAL.inc()
        raw_response = requests.post(
            settings.BS_UPSTREAM_API_ENDPOINT + "/score-submit.php",
            params=request.GET,
            headers=headers,
            json=body_parsed,
            timeout=GROOVESTATS_TIMEOUT,
        )
        gs_response = raw_response.json()
        logger.info(gs_response)
    except (requests.Timeout, requests.ConnectionError):
        GS_POST_REQUESTS_ERRORS_TOTAL.inc()

        if require_gs:
            return JsonResponse(GROOVESTATS_RESPONSES["GROOVESTATS_DEAD"], status=504)

    except json.JSONDecodeError as e:
        GS_POST_REQUESTS_ERRORS_TOTAL.inc()
        sentry_sdk.set_context("GS", {"raw_response": raw_response.content, "status": raw_response.status_code})
        sentry_sdk.capture_exception(e)

        if require_gs:
            return JsonResponse(GROOVESTATS_RESPONSES["GROOVESTATS_DEAD"], status=504)

    except Exception:  # catchall for incrementing metrics; reraise to let sentry catch it as an unhandled exception
        GS_POST_REQUESTS_ERRORS_TOTAL.inc()
        raise

    return gs_response


@csrf_exempt
def score_submit(request):
    try:
        players = parse_players(request)
        body_parsed = json.loads(request.body)
    except (ValueError, json.JSONDecodeError) as e:
        sentry_sdk.capture_exception(e)
        return JsonResponse(data=GROOVESTATS_RESPONSES["PLAYERS_VALIDATION_ERROR"], status=400)

    max_results = int(request.GET.get("maxLeaderboardResults", 1))

    player_instances = [p["player_instance"] for p in players.values()]
    # if player doesn't exist we need to call GS to verify the key for the first time
    gs_integrations = [p and p.gs_integration or GSIntegration.REQUIRE for p in player_instances]
    should_attempt_gs = any(g != GSIntegration.SKIP for g in gs_integrations)
    require_gs = any(g == GSIntegration.REQUIRE for g in gs_integrations)

    gs_response = {}
    if should_attempt_gs:
        gs_response = _post_gs(request, body_parsed, require_gs)

    if isinstance(gs_response, JsonResponse):
        return gs_response

    handle_scores(body_parsed, gs_response, players)

    player = list(players.values())[0]
    set_sentry_user(request, player["player_instance"])  # doing it again, because we could have created a new player

    final_response, response_headers = _make_score_submit_response(gs_response, players, max_results)

    return JsonResponse(data=final_response, headers=response_headers)


def handle_scores(body_parsed, gs_response, players):
    for player_index, player in players.items():
        player_id = f"player{player_index}"
        chart_hash = player["chartHash"]
        gs_api_key = player["gsApiKey"]
        gs_player = gs_response.get(player_id, {})
        is_ranked = gs_player.get("isRanked", False)

        song: Song
        song, _ = Song.objects.get_or_create(hash=chart_hash)
        song.set_ranked(is_ranked)

        player_instance = get_or_create_player(gs_api_key)
        player["player_instance"] = player_instance
        player_instance.update_name_and_tag(gs_player)

        _, old_score = song.get_highscore(player_instance, "itg")  # GS only informs about ITG score result & delta

        score_submission = body_parsed[player_id]
        comment = score_submission.get("comment", "")
        used_cmod = score_submission.get("usedCmod", None)
        judgments = score_submission.get("judgmentCounts", None)

        can_skip = player_instance.gs_integration == GSIntegration.SKIP
        gs_status = GSStatus.OK if gs_player else (GSStatus.SKIPPED if can_skip else GSStatus.ERROR)
        new_score = player_instance.scores.create(
            song=song,
            itg_score=score_submission["score"],
            comment=comment,
            rate=score_submission.get("rate", 100),
            used_cmod=used_cmod,
            judgments=judgments,
            gs_status=gs_status,
        )

        handle_score_results(player, old_score, new_score)
