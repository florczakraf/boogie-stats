import json

import pytest
import requests_mock as requests_mock_lib

from boogiestats.boogie_api.models import Song, Player, Score
from boogiestats.boogie_api.views import GROOVESTATS_ENDPOINT, GROOVESTATS_RESPONSES


@pytest.fixture(autouse=True)
def requests_mock():
    with requests_mock_lib.Mocker() as mock:
        yield mock


def test_player_scores_without_api_keys(client):
    response = client.get("/player-scores.php", data={"chartHashP1": "01234567890ABCDEF"})

    assert response.json() == GROOVESTATS_RESPONSES["PLAYERS_VALIDATION_ERROR"]


@pytest.fixture
def gs_api_key():
    return "abcdef0123456789" * 4


@pytest.mark.parametrize("player_index", [1, 2])
def test_player_scores_given_groovestats_unranked_song_that_we_dont_track(
    client, gs_api_key, requests_mock, player_index
):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
        }
    }
    requests_mock.get(GROOVESTATS_ENDPOINT + "/player-scores.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_X_Api_Key_Player_{player_index}": gs_api_key,
    }
    response = client.get(
        "/player-scores.php",
        data={f"chartHashP{player_index}": "0123456789ABCDEF"},
        **kwargs,
    )

    assert response.json() == {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": True,
            "gsLeaderboard": [],
        }
    }


@pytest.mark.parametrize("player_index", [1, 2])
def test_player_scores_given_groovestats_ranked_song(client, gs_api_key, requests_mock, player_index):
    ranked_song = {
        f"player{player_index}": {
            "chartHash": "76957dd1f96f764d",
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
                }
            ],
        }
    }
    requests_mock.get(GROOVESTATS_ENDPOINT + "/player-scores.php", text=json.dumps(ranked_song))
    kwargs = {
        f"HTTP_X_Api_Key_Player_{player_index}": gs_api_key,
    }
    response = client.get("/player-scores.php", data={f"chartHashP{player_index}": "76957dd1f96f764d"}, **kwargs)

    assert response.json() == ranked_song


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
    s.scores.create(player=some_player, score=8495, comment="C420", profile_name="1 2 3 4")
    s.scores.create(player=other_player, score=8595, comment="C420", profile_name="a b c d")

    return s


@pytest.mark.parametrize("player_index", [1, 2])
def test_player_leaderboards_requires_max_leaderboard_results_param(client, gs_api_key, player_index):
    kwargs = {
        f"HTTP_X_Api_Key_Player_{player_index}": gs_api_key,
    }
    response = client.get("/player-leaderboards.php", data={f"chartHashP{player_index}": "0123456789ABCDEF"}, **kwargs)
    assert response.json() == GROOVESTATS_RESPONSES["MISSING_LEADERBOARDS_LIMIT"]


@pytest.mark.parametrize("player_index", [1, 2])
def test_player_leaderboards_given_groovestats_unranked_song_that_we_dont_track(
    client, gs_api_key, requests_mock, player_index
):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
        }
    }
    requests_mock.get(
        GROOVESTATS_ENDPOINT + "/player-leaderboards.php",
        text=json.dumps(unranked_song),
    )
    kwargs = {
        f"HTTP_X_Api_Key_Player_{player_index}": gs_api_key,
    }
    response = client.get(
        "/player-leaderboards.php",
        data={f"chartHashP{player_index}": "0123456789ABCDEF", "maxLeaderboardResults": 3},
        **kwargs,
    )

    assert response.json() == {
        f"player{player_index}": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": True,
            "gsLeaderboard": [],
        }
    }


@pytest.mark.parametrize("player_index", [1, 2])
def test_player_leaderboards_given_groovestats_ranked_song(client, gs_api_key, requests_mock, player_index):
    ranked_song = {
        f"player{player_index}": {
            "chartHash": "76957dd1f96f764d",
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
        f"HTTP_X_Api_Key_Player_{player_index}": gs_api_key,
    }
    response = client.get(
        "/player-leaderboards.php",
        data={f"chartHashP{player_index}": "76957dd1f96f764d", "maxLeaderboardResults": 3},
        **kwargs,
    )

    assert response.json() == ranked_song


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_given_groovestats_ranked_song(client, gs_api_key, requests_mock, player_index):
    expected_result = {
        f"player{player_index}": {
            "chartHash": "76957dd1f96f764d",
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
        f"HTTP_X_Api_Key_Player_{player_index}": gs_api_key,
    }
    response = client.post(
        f"/score-submit.php?chartHashP{player_index}=76957dd1f96f764d&maxLeaderboardResults=3",
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

    assert Song.objects.count() == 0
    assert Score.objects.count() == 0
    assert Player.objects.count() == 0
    assert response.json() == expected_result


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_given_groovestats_unranked_song_that_we_dont_track_yet(
    client, gs_api_key, requests_mock, player_index
):
    unranked_song = {
        f"player{player_index}": {
            "chartHash": "76957dd1f96f764e",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 5805,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    kwargs = {
        f"HTTP_X_Api_Key_Player_{player_index}": gs_api_key,
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
    assert Score.objects.count() == 1
    assert Player.objects.count() == 1
    player = Player.objects.first()
    machine_tag = player.machine_tag
    assert response.json() == {
        f"player{player_index}": {
            "chartHash": "76957dd1f96f764e",
            "isRanked": True,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": machine_tag,
                    "score": 5805,
                    "date": song.get_highscore(player)[1].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isSelf": True,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": machine_tag,
                }
            ],
            "scoreDelta": 5805,
            "result": "score-added",
        }
    }


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_given_groovestats_unranked_song_and_better_score(
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
        f"HTTP_X_Api_Key_Player_{player_index}": some_player_gs_api_key,
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


@pytest.mark.parametrize("player_index", [1, 2])
def test_score_submit_given_groovestats_unranked_song_and_worse_score(
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
        f"HTTP_X_Api_Key_Player_{player_index}": some_player_gs_api_key,
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
