import json

import pytest
import requests_mock as requests_mock_lib

from boogie_api.models import Song, Player, Score
from boogie_api.views import GROOVESTATS_ENDPOINT, GROOVESTATS_RESPONSES


@pytest.fixture(autouse=True)
def requests_mock():
    with requests_mock_lib.Mocker() as mock:
        yield mock


def test_player_scores_without_chart_hash(client):
    response = client.get("/player-scores.php")

    assert response.json() == GROOVESTATS_RESPONSES["MISSING_CHARTS"]


def test_player_scores_without_api_keys(client):
    response = client.get("/player-scores.php", data={"chartHashP1": "01234567890ABCDEF"})

    assert response.json() == GROOVESTATS_RESPONSES["MISSING_API_KEYS"]


@pytest.fixture
def p1_gs_api_key():
    return "abcdef0123456789" * 4


def test_player_scores_given_groovestats_unranked_song_that_we_dont_track(client, p1_gs_api_key, requests_mock):
    unranked_song = {
        "player1": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
        }
    }
    requests_mock.get(GROOVESTATS_ENDPOINT + "/player-scores.php", text=json.dumps(unranked_song))
    response = client.get(
        "/player-scores.php",
        data={"chartHashP1": "0123456789ABCDEF"},
        HTTP_X_Api_Key_Player_1=p1_gs_api_key,
    )

    assert response.json() == {
        "player1": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": True,
            "gsLeaderboard": [],
        }
    }


def test_player_scores_given_groovestats_ranked_song(client, p1_gs_api_key, requests_mock):
    ranked_song = {
        "player1": {
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
    response = client.get(
        "/player-scores.php",
        data={"chartHashP1": "76957dd1f96f764d"},
        HTTP_X_Api_Key_Player_1=p1_gs_api_key,
    )

    assert response.json() == ranked_song


@pytest.fixture
def some_player_gs_api_key():
    return "1234432112344321"


@pytest.fixture
def some_player(some_player_gs_api_key):
    bs_api_key = Player.gs_api_key_to_bs_api_key(some_player_gs_api_key)
    return Player.objects.create(api_key=bs_api_key, machine_tag="1234")


@pytest.fixture
def other_player_gs_api_key():
    return "AAAABBBBCCCCDDDD"


@pytest.fixture
def other_player(other_player_gs_api_key):
    bs_api_key = Player.gs_api_key_to_bs_api_key(other_player_gs_api_key)
    return Player.objects.create(api_key=bs_api_key, machine_tag="ABCD")


@pytest.fixture
def song(some_player, other_player):
    s = Song.objects.create(hash="0123456789ABCDEF")
    s.scores.create(player=some_player, score=8495, comment="C420", profile_name="1 2 3 4")
    s.scores.create(player=other_player, score=8595, comment="C420", profile_name="a b c d")

    return s


def test_player_scores_given_groovestats_unranked_song_that_we_track_doesnt_call_groovestats(
    client, song, p1_gs_api_key, other_player
):
    response = client.get(
        "/player-scores.php",
        data={"chartHashP1": "0123456789ABCDEF"},
        HTTP_X_Api_Key_Player_1=p1_gs_api_key,
    )

    assert response.json() == {
        "player1": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": True,
            "gsLeaderboard": [
                {
                    "date": song.get_highscore(other_player)[1].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isFail": False,
                    "isRival": False,
                    "isSelf": False,
                    "machineTag": "ABCD",
                    "name": "ABCD",
                    "rank": 1,
                    "score": 8595,
                }
            ],
        }
    }


def test_player_leaderboards_requires_max_leaderboard_results_param(client, p1_gs_api_key):
    response = client.get(
        "/player-leaderboards.php",
        data={"chartHashP1": "0123456789ABCDEF"},
        HTTP_X_Api_Key_Player_1=p1_gs_api_key,
    )
    assert response.json() == GROOVESTATS_RESPONSES["MISSING_LEADERBOARDS_LIMIT"]


def test_player_leaderboards_given_groovestats_unranked_song_that_we_dont_track(client, p1_gs_api_key, requests_mock):
    unranked_song = {
        "player1": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
        }
    }
    requests_mock.get(
        GROOVESTATS_ENDPOINT + "/player-leaderboards.php",
        text=json.dumps(unranked_song),
    )
    response = client.get(
        "/player-leaderboards.php",
        data={"chartHashP1": "0123456789ABCDEF", "maxLeaderboardResults": 3},
        HTTP_X_Api_Key_Player_1=p1_gs_api_key,
    )

    assert response.json() == {
        "player1": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": True,
            "gsLeaderboard": [],
        }
    }


def test_player_leaderboards_given_groovestats_ranked_song(client, p1_gs_api_key, requests_mock):
    ranked_song = {
        "player1": {
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
    response = client.get(
        "/player-leaderboards.php",
        data={"chartHashP1": "76957dd1f96f764d", "maxLeaderboardResults": 3},
        HTTP_X_Api_Key_Player_1=p1_gs_api_key,
    )

    assert response.json() == ranked_song


def test_player_leaderboards_given_groovestats_unranked_song_that_we_track_doesnt_call_groovestats(
    client, song, p1_gs_api_key, some_player, other_player
):
    response = client.get(
        "/player-leaderboards.php",
        data={"chartHashP1": "0123456789ABCDEF", "maxLeaderboardResults": 3},
        HTTP_X_Api_Key_Player_1=p1_gs_api_key,
    )

    assert response.json() == {
        "player1": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": True,
            "gsLeaderboard": [
                {
                    "date": song.get_highscore(other_player)[1].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isFail": False,
                    "isRival": False,
                    "isSelf": False,
                    "machineTag": "ABCD",
                    "name": "ABCD",
                    "rank": 1,
                    "score": 8595,
                },
                {
                    "date": song.get_highscore(some_player)[1].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isFail": False,
                    "isRival": False,
                    "isSelf": False,
                    "machineTag": "1234",
                    "name": "1234",
                    "rank": 2,
                    "score": 8495,
                },
            ],
        }
    }


def test_score_submit_given_groovestats_ranked_song(client, p1_gs_api_key, requests_mock):
    expected_result = {
        "player1": {
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
    response = client.post(
        "/score-submit.php?chartHashP1=76957dd1f96f764d&maxLeaderboardResults=3",
        data={
            "player1": {
                "score": 5805,
                "comment": "50e, 42g, 8d, 11wo, 4m, C300",
                "rate": 100,
            }
        },
        content_type="application/json",
        HTTP_X_Api_Key_Player_1=p1_gs_api_key,
    )

    assert Song.objects.count() == 0
    assert Score.objects.count() == 0
    assert Player.objects.count() == 0
    assert response.json() == expected_result


def test_score_submit_given_groovestats_unranked_song_that_we_dont_track_yet(client, p1_gs_api_key, requests_mock):
    unranked_song = {
        "player1": {
            "chartHash": "76957dd1f96f764e",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 5805,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    response = client.post(
        "/score-submit.php?chartHashP1=76957dd1f96f764e&maxLeaderboardResults=3",
        data={
            "player1": {
                "score": 5805,
                "comment": "50e, 42g, 8d, 11wo, 4m, C300",
                "rate": 100,
            }
        },
        content_type="application/json",
        HTTP_X_Api_Key_Player_1=p1_gs_api_key,
    )

    assert Song.objects.count() == 1
    song = Song.objects.first()
    assert Score.objects.count() == 1
    assert Player.objects.count() == 1
    player = Player.objects.first()
    assert response.json() == {
        "player1": {
            "chartHash": "76957dd1f96f764e",
            "isRanked": True,
            "gsLeaderboard": [
                {
                    "rank": 1,
                    "name": "bc37",
                    "score": 5805,
                    "date": song.get_highscore(player)[1].submission_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "isSelf": True,
                    "isRival": False,
                    "isFail": False,
                    "machineTag": "bc37",
                }
            ],
            "scoreDelta": 5805,
            "result": "score-added",
        }
    }


def test_score_submit_given_groovestats_unranked_song_and_better_score(
    client, song, some_player, other_player, requests_mock, some_player_gs_api_key
):
    unranked_song = {
        "player1": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 5805,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    response = client.post(
        "/score-submit.php?chartHashP1=0123456789ABCDEF&maxLeaderboardResults=3",
        data={
            "player1": {
                "score": 9999,
                "comment": "50e, 42g, 8d, 11wo, 4m, C300",
                "rate": 100,
            }
        },
        content_type="application/json",
        HTTP_X_Api_Key_Player_1=some_player_gs_api_key,
    )

    assert Song.objects.count() == 1
    song = Song.objects.first()
    assert Score.objects.count() == 3
    assert Player.objects.count() == 2
    assert response.json() == {
        "player1": {
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


def test_score_submit_given_groovestats_unranked_song_and_worse_score(
    client, song, some_player, other_player, requests_mock, some_player_gs_api_key
):
    unranked_song = {
        "player1": {
            "chartHash": "0123456789ABCDEF",
            "isRanked": False,
            "gsLeaderboard": [],
            "scoreDelta": 5805,
        }
    }
    requests_mock.post(GROOVESTATS_ENDPOINT + "/score-submit.php", text=json.dumps(unranked_song))
    response = client.post(
        "/score-submit.php?chartHashP1=0123456789ABCDEF&maxLeaderboardResults=3",
        data={
            "player1": {
                "score": 1000,
                "comment": "50e, 42g, 8d, 11wo, 4m, C300",
                "rate": 100,
            }
        },
        content_type="application/json",
        HTTP_X_Api_Key_Player_1=some_player_gs_api_key,
    )

    assert Song.objects.count() == 1
    song = Song.objects.first()
    assert Score.objects.count() == 3
    assert Player.objects.count() == 2
    assert response.json() == {
        "player1": {
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
