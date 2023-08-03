import json
from unittest.mock import Mock

import pytest
import requests_mock as requests_mock_lib

from boogiestats import __version__ as boogiestats_version
from boogiestats.boogie_api.models import Song, Player, Score, LeaderboardSource
from boogiestats.boogie_api.views import GROOVESTATS_ENDPOINT, GROOVESTATS_RESPONSES, create_headers, LB_SOURCE_MAPPING


@pytest.fixture(autouse=True)
def requests_mock():
    with requests_mock_lib.mock(case_sensitive=True) as mock:
        yield mock


def test_player_scores_without_api_keys(client):
    response = client.get("/player-scores.php", data={"chartHashP1": "01234567890ABCDEF"})

    assert response.json() == GROOVESTATS_RESPONSES["PLAYERS_VALIDATION_ERROR"]
    assert response.status_code == 400


@pytest.fixture
def gs_api_key():
    return "abcdef0123456789" * 4


@pytest.mark.parametrize("player_index", [1, 2])
def test_player_scores_when_lb_source_is_bs(client, gs_api_key, requests_mock, player_index):
    hash = "0123456789ABCDEF"
    unranked_song = {
        f"player{player_index}": {
            "chartHash": hash,
            "isRanked": False,
            "gsLeaderboard": [],
        }
    }
    requests_mock.get(GROOVESTATS_ENDPOINT + "/player-scores.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": gs_api_key,
    }
    response = client.get(
        "/player-scores.php",
        data={f"chartHashP{player_index}": hash},
        **kwargs,
    )

    assert len(requests_mock.request_history) == 1
    assert requests_mock.last_request.qs[f"chartHashP{player_index}"] == [hash]
    assert requests_mock.last_request.headers[f"x-api-key-player-{player_index}"] == gs_api_key
    assert response.json() == {
        f"player{player_index}": {
            "chartHash": hash,
            "isRanked": True,
            "gsLeaderboard": [],
        }
    }
    assert response.headers[f"bs-leaderboard-player-{player_index}"] == "BS"


@pytest.mark.parametrize("player_index", [1, 2])
def test_player_scores_when_lb_source_is_gs(client, gs_api_key, requests_mock, player_index):
    Player.objects.create(
        gs_api_key=gs_api_key, machine_tag="1234", leaderboard_source=LeaderboardSource.GROOVESTATS_ITG
    )

    hash = "76957dd1f96f764d"
    ranked_song = {
        f"player{player_index}": {
            "chartHash": hash,
            "isRanked": False,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": "Ash ketchum!",
                    "score": 10000,
                    "date": "2018-02-07 19:49:20",
                    "isSelf": False,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "A5H!",
                }
            ],
        }
    }
    requests_mock.get(GROOVESTATS_ENDPOINT + "/player-scores.php", text=json.dumps(ranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": gs_api_key,
    }
    response = client.get("/player-scores.php", data={f"chartHashP{player_index}": hash}, **kwargs)

    assert len(requests_mock.request_history) == 1
    assert requests_mock.last_request.qs[f"chartHashP{player_index}"] == [hash]
    assert requests_mock.last_request.headers[f"x-api-key-player-{player_index}"] == gs_api_key
    assert requests_mock.last_request.headers["user-agent"].endswith(f"via BoogieStats/{boogiestats_version}")
    assert response.json() == ranked_song
    assert response.headers[f"bs-leaderboard-player-{player_index}"] == "GS"


def test_create_headers_filters_headers():
    request = Mock(headers={"Host": "boogie.stats", "x-api-key-player-1": "foo", "x-api-key-player-2": "bar"})
    assert create_headers(request) == {
        "User-Agent": "Anonymous via BoogieStats/0.0.1",
        "x-api-key-player-1": "foo",
        "x-api-key-player-2": "bar",
    }


def test_create_headers_wraps_user_agent():
    request = Mock(headers={"User-Agent": "ITGmania/0.5.1"})
    assert create_headers(request) == {"User-Agent": f"ITGmania/0.5.1 via BoogieStats/{boogiestats_version}"}


def test_create_headers_adds_user_agent_when_missing():
    request = Mock(headers={})
    assert create_headers(request) == {"User-Agent": f"Anonymous via BoogieStats/{boogiestats_version}"}


@pytest.fixture
def some_player_gs_api_key():
    return "1234432112344321"


@pytest.fixture
def some_player(some_player_gs_api_key):
    return Player.objects.create(gs_api_key=some_player_gs_api_key, machine_tag="1234")


@pytest.fixture
def other_player_gs_api_key():
    return "AAAABBBBCCCCDDDD"


@pytest.fixture
def other_player(other_player_gs_api_key):
    return Player.objects.create(gs_api_key=other_player_gs_api_key, machine_tag="ABCD")


@pytest.fixture
def song(some_player, other_player):
    s = Song.objects.create(hash="0123456789ABCDEF")
    s.scores.create(player=some_player, score=8495, comment="C420", rate=100)
    s.scores.create(player=other_player, score=8595, comment="C420", rate=100)

    return s


@pytest.mark.parametrize("player_index", [1, 2])
def test_player_leaderboards_when_lb_source_is_gs(client, gs_api_key, requests_mock, player_index):
    Player.objects.create(
        gs_api_key=gs_api_key, machine_tag="1234", leaderboard_source=LeaderboardSource.GROOVESTATS_ITG
    )

    ranked_song = {
        f"player{player_index}": {
            "chartHash": "76957dd1f96f764d",
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": "Ash ketchum!",
                    "score": 10000,
                    "date": "2018-02-07 19:49:20",
                    "isSelf": False,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "A5H!",
                },
                {
                    "rank": 2,
                    "name": "foo",
                    "score": 9900,
                    "date": "2014-02-07 19:49:20",
                    "isSelf": False,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "FOOB",
                },
            ],
        }
    }
    requests_mock.get(GROOVESTATS_ENDPOINT + "/player-leaderboards.php", text=json.dumps(ranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": gs_api_key,
    }
    response = client.get(
        "/player-leaderboards.php",
        data={f"chartHashP{player_index}": "76957dd1f96f764d", "maxLeaderboardResults": 3},
        **kwargs,
    )

    assert response.json() == ranked_song
    assert response.headers[f"bs-leaderboard-player-{player_index}"] == "GS"


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_when_lb_source_is_gs(client, gs_api_key, requests_mock, player_index):
    Player.objects.create(
        gs_api_key=gs_api_key, machine_tag="1234", leaderboard_source=LeaderboardSource.GROOVESTATS_ITG
    )

    hash = "76957dd1f96f764d"
    expected_result = {
        f"player{player_index}": {
            "chartHash": hash,
            "isRanked": True,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": "Ash ketchum!",
                    "score": 10000,
                    "date": "2018-02-07 19:49:20",
                    "isSelf": False,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "A5H!",
                },
                {
                    "rank": 34,
                    "name": "wermi",
                    "score": 8514,
                    "date": "2020-08-23 23:41:21",
                    "isSelf": False,
                    "isRival": True,
                    "isFail": False,
                    "machineTag": "nela",
                },
                {
                    "rank": 38,
                    "name": "andr_test",
                    "score": 5809,
                    "date": "2021-11-13 10:33:34",
                    "isSelf": True,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "DUPA",
                },
            ],
            "scoreDelta": 5809,
            "result": "score-added",
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(expected_result))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}={hash}&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "score": 5805,
                "comment": "50e, 42g, 8d, 11wo, 4m, C300",
                "rate": 100,
            }
        },
        content_type="application/json",
        **kwargs,
    )

    assert Song.objects.count() == 1
    song = Song.objects.first()
    assert song.hash == hash
    assert song.gs_ranked is True
    assert Score.objects.count() == 1
    assert Player.objects.count() == 1
    assert response.json() == expected_result
    assert len(requests_mock.request_history) == 1
    assert requests_mock.last_request.qs[f"chartHashP{player_index}"] == [hash]
    assert requests_mock.last_request.qs["maxLeaderboardResults"] == ["3"]
    assert requests_mock.last_request.headers[f"x-api-key-player-{player_index}"] == gs_api_key
    assert requests_mock.last_request.headers["user-agent"].endswith(f"via BoogieStats/{boogiestats_version}")
    player = Player.objects.first()
    assert player.machine_tag == "DUPA"
    assert player.name == "andr_test"
    assert response.headers[f"bs-leaderboard-player-{player_index}"] == "GS"


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_for_untracked_song_when_lb_source_is_bs_itg(client, gs_api_key, requests_mock, player_index):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "76957dd1f96f764e",
            "isRanked": True,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": "Ash ketchum!",
                    "score": 10000,
                    "date": "2018-02-07 19:49:20",
                    "isSelf": False,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "A5H!",
                },
                {
                    "rank": 2,
                    "name": "name",
                    "score": 5805,
                    "date": "2018-02-07 19:49:20",
                    "isSelf": True,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "tag",
                },
            ],
            "scoreDelta": 5805,
            "result": "score-added",
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}=76957dd1f96f764e&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "score": 5805,
                "comment": "50e, 42g, 8d, 11wo, 4m, C300",
                "rate": 100,
            }
        },
        content_type="application/json",
        **kwargs,
    )

    assert Song.objects.count() == 1
    song = Song.objects.first()
    assert song.hash == "76957dd1f96f764e"
    assert song.gs_ranked is True
    assert Score.objects.count() == 1
    assert Player.objects.count() == 1
    player = Player.objects.first()
    assert response.json() == {
        f"player{player_index}": {
            "chartHash": "76957dd1f96f764e",
            "isRanked": True,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": player.name,
                    "score": 5805,
                    "date": song.get_highscore(player)[1].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isSelf": True,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": player.machine_tag,
                }
            ],
            "scoreDelta": 5805,
            "result": "score-added",
        }
    }
    assert response.headers[f"bs-leaderboard-player-{player_index}"] == "BS"


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_with_better_score_when_lb_source_is_bs(
    client, song, some_player, other_player, requests_mock, some_player_gs_api_key, player_index
):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 5805,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}=0123456789ABCDEF&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "score": 9999,
                "comment": "50e, 42g, 8d, 11wo, 4m, C300",
                "rate": 100,
            }
        },
        content_type="application/json",
        **kwargs,
    )

    assert Song.objects.count() == 1
    song = Song.objects.first()
    assert Score.objects.count() == 3
    assert Player.objects.count() == 2
    assert response.json() == {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": True,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": "1234",
                    "score": 9999,
                    "date": song.get_highscore(some_player)[1].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isSelf": True,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "1234",
                },
                {
                    "rank": 2,
                    "name": "ABCD",
                    "score": 8595,
                    "date": song.get_highscore(other_player)[1].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isSelf": False,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "ABCD",
                },
            ],
            "scoreDelta": 9999 - 8495,
            "result": "improved",
        }
    }
    assert response.headers[f"bs-leaderboard-player-{player_index}"] == "BS"


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_with_worse_score_when_lb_source_is_bs(
    client, song, some_player, other_player, requests_mock, some_player_gs_api_key, player_index
):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 5805,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}=0123456789ABCDEF&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "score": 1000,
                "comment": "50e, 42g, 8d, 11wo, 4m, C300",
                "rate": 100,
            }
        },
        content_type="application/json",
        **kwargs,
    )

    assert Song.objects.count() == 1
    song = Song.objects.first()
    assert Score.objects.count() == 3
    assert Player.objects.count() == 2
    assert response.json() == {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": True,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": "ABCD",
                    "score": 8595,
                    "date": song.get_highscore(other_player)[1].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isSelf": False,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "ABCD",
                },
                {
                    "rank": 2,
                    "name": "1234",
                    "score": 8495,
                    "date": song.get_highscore(some_player)[1].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isSelf": True,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "1234",
                },
            ],
            "scoreDelta": 1000 - 8495,
            "result": "score-not-improved",
        }
    }
    assert response.headers[f"bs-leaderboard-player-{player_index}"] == "BS"


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_with_empty_comment(
    client, song, some_player, other_player, requests_mock, some_player_gs_api_key, player_index
):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "0123456789FFFFFF",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 5805,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}=0123456789ABCDEF&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "score": 1000,
                "comment": "",
                "rate": 100,
            }
        },
        content_type="application/json",
        **kwargs,
    )

    assert Song.objects.count() == 1
    assert Score.objects.count() == 3
    assert Player.objects.count() == 2
    assert len(response.json()[f"player{player_index}"]["gsLeaderboard"]) == 2


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_without_a_comment(
    client, song, some_player, other_player, requests_mock, some_player_gs_api_key, player_index
):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "0123456789FFFFFF",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 5805,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}=0123456789ABCDEF&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "score": 1000,
                "rate": 100,
            }
        },
        content_type="application/json",
        **kwargs,
    )

    assert Song.objects.count() == 1
    assert Score.objects.count() == 3
    assert Player.objects.count() == 2
    assert len(response.json()[f"player{player_index}"]["gsLeaderboard"]) == 2


@pytest.mark.parametrize("event_key", ["rpg", "itl"])
@pytest.mark.parametrize("player_index", [1, 2])
@pytest.mark.parametrize("lb_source", [LeaderboardSource.BOOGIESTATS_ITG, LeaderboardSource.GROOVESTATS_ITG])
def test_event_score_submit(
    client,
    some_player,
    requests_mock,
    some_player_gs_api_key,
    player_index,
    event_key,
    lb_source,
):
    some_player.leaderboard_source = lb_source
    some_player.save()

    gs_response = {
        f"player{player_index}": {
            "chartHash": "afc954d593fd8bbd",
            event_key: {"everything": "will be passed"},
            "gsLeaderboard": [],
            "scoreDelta": 8041,
            "result": "improved",
        }
    }

    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(gs_response))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}=afc954d593fd8bbd&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "score": 8351,
                "rate": 100,
            }
        },
        content_type="application/json",
        **kwargs,
    )

    assert Song.objects.count() == 1
    assert Score.objects.count() == 1
    event_results = response.json()[f"player{player_index}"][event_key]
    assert event_results["everything"] == "will be passed"
    assert response.headers[f"bs-leaderboard-player-{player_index}"] == LB_SOURCE_MAPPING[lb_source]


@pytest.mark.parametrize("event_key", ["rpg", "itl"])
@pytest.mark.parametrize("player_index", [1, 2])
@pytest.mark.parametrize("lb_source", [LeaderboardSource.BOOGIESTATS_ITG, LeaderboardSource.GROOVESTATS_ITG])
def test_event_player_scores(
    client, some_player, requests_mock, some_player_gs_api_key, player_index, event_key, lb_source
):
    some_player.leaderboard_source = lb_source
    some_player.save()

    gs_response = {
        f"player{player_index}": {
            "chartHash": "afc954d593fd8bbd",
            event_key: {"everything": "will be passed"},
            "gsLeaderboard": [],
            "scoreDelta": 8041,
            "isRanked": True,
            "result": "improved",
        }
    }

    requests_mock.get(GROOVESTATS_ENDPOINT + "/player-scores.php", text=json.dumps(gs_response))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    response = client.get(
        f"/player-scores.php?chartHashP{player_index}=afc954d593fd8bbd&maxLeaderboardResults=13",
        **kwargs,
    )

    assert Song.objects.count() == 0
    assert Score.objects.count() == 0
    event_results = response.json()[f"player{player_index}"][event_key]
    assert event_results["everything"] == "will be passed"
    assert response.headers[f"bs-leaderboard-player-{player_index}"] == LB_SOURCE_MAPPING[lb_source]


@pytest.mark.parametrize("event_key", ["rpg", "itl"])
@pytest.mark.parametrize("player_index", [1, 2])
@pytest.mark.parametrize("lb_source", [LeaderboardSource.BOOGIESTATS_ITG, LeaderboardSource.GROOVESTATS_ITG])
def test_event_player_leaderboards(
    client, some_player, requests_mock, some_player_gs_api_key, player_index, event_key, lb_source
):
    some_player.leaderboard_source = lb_source
    some_player.save()

    gs_response = {
        f"player{player_index}": {
            "chartHash": "afc954d593fd8bbd",
            event_key: {"everything": "will be passed"},
            "gsLeaderboard": [],
            "scoreDelta": 8041,
            "isRanked": True,
            "result": "improved",
        }
    }

    requests_mock.get(GROOVESTATS_ENDPOINT + "/player-leaderboards.php", text=json.dumps(gs_response))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    response = client.get(
        f"/player-leaderboards.php?chartHashP{player_index}=afc954d593fd8bbd&maxLeaderboardResults=13",
        **kwargs,
    )

    assert Song.objects.count() == 0
    assert Score.objects.count() == 0
    event_results = response.json()[f"player{player_index}"][event_key]
    assert event_results["everything"] == "will be passed"
    assert response.headers[f"bs-leaderboard-player-{player_index}"] == LB_SOURCE_MAPPING[lb_source]


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_with_some_judgments(
    client, song, some_player, other_player, requests_mock, some_player_gs_api_key, player_index
):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 7560,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}=0123456789ABCDEF&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "comment": "30e, 27g, 1m, No Dec/WO",
                "judgmentCounts": {
                    "excellent": 30,
                    "fantastic": 13,
                    "fantasticPlus": 21,
                    "great": 27,
                    "holdsHeld": 3,
                    "minesHit": 1,
                    "miss": 1,
                    "rollsHeld": 2,
                    "totalHolds": 6,
                    "totalMines": 5,
                    "totalRolls": 3,
                    "totalSteps": 92,
                },
                "rate": 105,
                "score": 7560,
                "usedCmod": False,
            },
        },
        content_type="application/json",
        **kwargs,
    )

    assert Score.objects.count() == 3
    assert len(response.json()[f"player{player_index}"]["gsLeaderboard"]) == 2
    score = Score.objects.last()
    assert score.used_cmod is False
    assert score.has_judgments is True
    assert score.excellents == 30
    assert score.fantastics == 13
    assert score.fantastics_plus == 21
    assert score.greats == 27
    assert score.misses == 1
    assert score.decents == 0
    assert score.way_offs == 0
    assert score.holds_held == 3
    assert score.mines_hit == 1
    assert score.rolls_held == 2
    assert score.total_holds == 6
    assert score.total_mines == 5
    assert score.total_rolls == 3
    assert score.total_steps == 92
    assert score.rate == 105
    assert score.score == 7560


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_with_all_judgments(
    client, song, some_player, other_player, requests_mock, some_player_gs_api_key, player_index
):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 5340,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}=0123456789ABCDEF&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "comment": "20e, 19g, 4d, 4wo, 4m",
                "judgmentCounts": {
                    "decent": 4,
                    "excellent": 20,
                    "fantastic": 7,
                    "fantasticPlus": 31,
                    "great": 19,
                    "holdsHeld": 3,
                    "minesHit": 0,
                    "miss": 4,
                    "rollsHeld": 0,
                    "totalHolds": 5,
                    "totalMines": 0,
                    "totalRolls": 0,
                    "totalSteps": 89,
                    "wayOff": 4,
                },
                "rate": 100,
                "score": 5340,
                "usedCmod": False,
            },
        },
        content_type="application/json",
        **kwargs,
    )

    assert Song.objects.count() == 1
    assert Score.objects.count() == 3
    assert Player.objects.count() == 2
    assert len(response.json()[f"player{player_index}"]["gsLeaderboard"]) == 2
    score = Score.objects.last()
    assert score.used_cmod is False
    assert score.has_judgments is True
    assert score.excellents == 20
    assert score.fantastics == 7
    assert score.fantastics_plus == 31
    assert score.greats == 19
    assert score.misses == 4
    assert score.decents == 4
    assert score.way_offs == 4
    assert score.holds_held == 3
    assert score.mines_hit == 0
    assert score.rolls_held == 0
    assert score.total_holds == 5
    assert score.total_mines == 0
    assert score.total_rolls == 0
    assert score.total_steps == 89
    assert score.rate == 100
    assert score.score == 5340


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_with_cmod_info(
    client, song, some_player, other_player, requests_mock, some_player_gs_api_key, player_index
):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 7560,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}=0123456789ABCDEF&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "comment": "30e, 27g, 1m, C555, No Dec/WO",
                "rate": 100,
                "score": 7560,
                "usedCmod": True,
            },
        },
        content_type="application/json",
        **kwargs,
    )

    assert Score.objects.count() == 3
    assert len(response.json()[f"player{player_index}"]["gsLeaderboard"]) == 2
    score = Score.objects.last()
    assert not score.has_judgments
    assert score.used_cmod is True


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_with_no_cmod_info_but_cmod_comment(
    client, song, some_player, other_player, requests_mock, some_player_gs_api_key, player_index
):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 7560,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}=0123456789ABCDEF&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "comment": "30e, 27g, 1m, C350, No Dec/WO",
                "rate": 105,
                "score": 7560,
            },
        },
        content_type="application/json",
        **kwargs,
    )

    assert Score.objects.count() == 3
    assert len(response.json()[f"player{player_index}"]["gsLeaderboard"]) == 2
    score = Score.objects.last()
    assert not score.has_judgments
    assert score.used_cmod is True


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_with_no_cmod_info(
    client, song, some_player, other_player, requests_mock, some_player_gs_api_key, player_index
):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 7560,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}=0123456789ABCDEF&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "comment": "30e, 27g, 1m, No Dec/WO",
                "rate": 105,
                "score": 7560,
            },
        },
        content_type="application/json",
        **kwargs,
    )

    assert Score.objects.count() == 3
    assert len(response.json()[f"player{player_index}"]["gsLeaderboard"]) == 2
    score = Score.objects.last()
    assert not score.has_judgments
    assert score.used_cmod is False


def test_score_submit_with_two_players_playing_the_same_song_when_lb_source_is_bs(client, gs_api_key, requests_mock):
    unranked_songs = {
        "player1": {
            "chartHash": "aaaaadd1f96f764e",
            "isRanked": True,
            "gsLeaderboard": [],
            "scoreDelta": 5500,
        },
        "player2": {
            "chartHash": "aaaaadd1f96f764e",
            "isRanked": True,
            "gsLeaderboard": [],
            "scoreDelta": 6500,
        },
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_songs))
    kwargs = {
        "HTTP_x_api_key_player_1": "abcdef0123456789" * 4,
        "HTTP_x_api_key_player_2": "abcdef0123456789"[::-1] * 4,
    }
    response = client.post(
        "/score-submit.php?chartHashP1=aaaaadd1f96f764e&chartHashP2=aaaaadd1f96f764e&maxLeaderboardResults=3",
        data={
            "player1": {
                "score": 5500,
                "comment": "foo",
                "rate": 100,
            },
            "player2": {
                "score": 6500,
                "comment": "bar",
                "rate": 100,
            },
        },
        content_type="application/json",
        **kwargs,
    )

    assert Song.objects.count() == 1
    song = Song.objects.first()
    assert song.hash == "aaaaadd1f96f764e"
    assert song.gs_ranked is True
    assert Score.objects.count() == 2
    assert Player.objects.count() == 2
    scores = Score.objects.all().order_by("-score")

    assert response.json() == {
        "player1": {
            "chartHash": "aaaaadd1f96f764e",
            "isRanked": True,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": scores[0].player.machine_tag,
                    "score": 6500,
                    "date": scores[0].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isSelf": False,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": scores[0].player.machine_tag,
                },
                {
                    "rank": 2,
                    "name": scores[1].player.machine_tag,
                    "score": 5500,
                    "date": scores[1].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isSelf": True,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": scores[1].player.machine_tag,
                },
            ],
            "scoreDelta": 5500,
            "result": "score-added",
        },
        "player2": {
            "chartHash": "aaaaadd1f96f764e",
            "isRanked": True,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": scores[0].player.machine_tag,
                    "score": 6500,
                    "date": scores[0].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isSelf": True,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": scores[0].player.machine_tag,
                },
                {
                    "rank": 2,
                    "name": scores[1].player.machine_tag,
                    "score": 5500,
                    "date": scores[1].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isSelf": False,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": scores[1].player.machine_tag,
                },
            ],
            "scoreDelta": 6500,
            "result": "score-added",
        },
    }
    assert response.headers["bs-leaderboard-player-1"] == "BS"
    assert response.headers["bs-leaderboard-player-2"] == "BS"


def test_score_submit_with_two_players_when_using_bs_itg_and_gs_itg_lbs(
    client, gs_api_key, some_player_gs_api_key, requests_mock
):
    Player.objects.create(
        gs_api_key=some_player_gs_api_key, machine_tag="1234", leaderboard_source=LeaderboardSource.GROOVESTATS_ITG
    )

    ranked_songs = {
        "player1": {
            "chartHash": "aaaaadd1f96f764e",
            "isRanked": False,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": "foo",
                    "score": 6500,
                    "date": "2021-11-13 10:33:34",
                    "isSelf": False,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "FOO",
                }
            ],
            "scoreDelta": 5500,
            "result": "score-added",
        },
        "player2": {
            "chartHash": "bbbbbdd1f96f764e",
            "isRanked": True,
            "gsLeaderboard": [],
            "scoreDelta": 6500,
        },
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(ranked_songs))
    kwargs = {
        "HTTP_x_api_key_player_1": some_player_gs_api_key,
        "HTTP_x_api_key_player_2": gs_api_key,
    }
    response = client.post(
        "/score-submit.php?chartHashP1=aaaaadd1f96f764e&chartHashP2=bbbbbdd1f96f764e&maxLeaderboardResults=3",
        data={
            "player1": {
                "score": 5500,
                "comment": "foo",
                "rate": 100,
            },
            "player2": {
                "score": 6500,
                "comment": "bar",
                "rate": 100,
            },
        },
        content_type="application/json",
        **kwargs,
    )

    assert Song.objects.count() == 2
    assert Score.objects.count() == 2
    assert Player.objects.count() == 2

    assert response.headers["bs-leaderboard-player-1"] == "GS"
    assert response.headers["bs-leaderboard-player-2"] == "BS"


@pytest.mark.parametrize("player_index", [1, 2])
@pytest.mark.parametrize("pull_gs_name_and_tag", [True, False])
def test_pulling_gs_name_and_tag(
    client, some_player, some_player_gs_api_key, requests_mock, player_index, pull_gs_name_and_tag
):
    some_player.pull_gs_name_and_tag = pull_gs_name_and_tag
    some_player.save()

    hash = "76957dd1f96f764d"
    expected_result = {
        f"player{player_index}": {
            "chartHash": hash,
            "isRanked": False,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": "andr_test",
                    "score": 5809,
                    "date": "2021-11-13 10:33:34",
                    "isSelf": True,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "DUPA",
                },
            ],
            "scoreDelta": 5809,
            "result": "score-added",
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(expected_result))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    client.post(
        f"/score-submit.php?chartHashP{player_index}={hash}&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "score": 5805,
                "comment": "50e, 42g, 8d, 11wo, 4m, C300",
                "rate": 100,
            }
        },
        content_type="application/json",
        **kwargs,
    )

    player = Player.objects.first()
    if pull_gs_name_and_tag:
        assert player.machine_tag == "DUPA"
        assert player.name == "andr_test"
    else:
        assert player.name == player.machine_tag == "1234"


@pytest.mark.parametrize("player_index", [1, 2])
@pytest.mark.parametrize("extra_attribute", [("name", "andr_test"), ("machineTag", "DUPA")])
def test_pulling_gs_name_and_tag_with_missing_attributes(
    client, some_player, some_player_gs_api_key, requests_mock, player_index, extra_attribute
):
    some_player.pull_gs_name_and_tag = True
    some_player.save()

    hash = "76957dd1f96f764d"
    expected_result = {
        f"player{player_index}": {
            "chartHash": hash,
            "isRanked": False,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "score": 5809,
                    "date": "2021-11-13 10:33:34",
                    "isSelf": True,
                    "isRival": False,
                    "isFail": False,
                },
            ],
            "scoreDelta": 5809,
            "result": "score-added",
        }
    }
    key, value = extra_attribute
    expected_result[f"player{player_index}"]["gsLeaderboard"][0][key] = value
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(expected_result))
    kwargs = {
        f"HTTP_x_api_key_player_{player_index}": some_player_gs_api_key,
    }
    client.post(
        f"/score-submit.php?chartHashP{player_index}={hash}&maxLeaderboardResults=3",
        data={
            f"player{player_index}": {
                "score": 5805,
                "comment": "50e, 42g, 8d, 11wo, 4m, C300",
                "rate": 100,
            }
        },
        content_type="application/json",
        **kwargs,
    )

    player = Player.objects.first()
    if key == "name":
        assert player.name == "andr_test"
        assert player.machine_tag == "1234"
    else:
        assert player.name == "1234"
        assert player.machine_tag == "DUPA"
