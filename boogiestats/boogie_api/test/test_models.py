import pytest
from django.core.exceptions import ValidationError
from django.db import transaction

from boogiestats.boogie_api.models import Song, Player


@pytest.fixture
def song():
    return Song.objects.create(hash="somesong")


@pytest.fixture
def other_song():
    return Song.objects.create(hash="othersong")


@pytest.fixture
def player(song, other_song):
    p = Player.objects.create(gs_api_key="playerkey", machine_tag="PL")
    p.scores.create(
        song=song,
        score=6442,
        comment="M400, OtherMod",
        profile_name="player profile",
    )
    p.scores.create(
        song=other_song,
        score=6666,
        comment="M400, OtherMod",
        profile_name="player profile",
    )
    return p


@pytest.fixture
def rival1(player, song):
    rival = Player.objects.create(gs_api_key="rival1key", machine_tag="RIV1")
    rival.scores.create(
        song=song,
        score=4553,
        comment="C500",
        profile_name="rival1 profile",
    )
    player.rivals.add(rival)
    player.save()
    return rival


@pytest.fixture
def rival2(player, song):
    rival = Player.objects.create(gs_api_key="rival2key", machine_tag="RIV2")
    rival.scores.create(
        song=song,
        score=7588,
        comment="C200",
        profile_name="rival2 profile",
    )
    player.rivals.add(rival)
    player.save()
    return rival


@pytest.fixture
def rival3(player, song):
    rival = Player.objects.create(gs_api_key="rival3key", machine_tag="RIV3")
    rival.scores.create(
        song=song,
        score=7700,
        comment="M550",
        profile_name="rival3 profile",
    )
    player.rivals.add(rival)
    player.save()
    return rival


@pytest.fixture
def rival4(player, song):
    rival = Player.objects.create(gs_api_key="rival4key", machine_tag="RIV4")
    rival.scores.create(
        song=song,
        score=7300,
        comment="M550",
        profile_name="rival4 profile",
    )
    player.rivals.add(rival)
    player.save()
    return rival


@pytest.fixture
def top_scores(song):
    for i in range(1, 21):
        p = Player.objects.create(gs_api_key=f"top{i}key", machine_tag=f"T{i}")
        p.scores.create(
            song=song,
            score=10_000 - i * 100,
            comment=f"M420, TOP{i}",
            profile_name=f"top{i} profile",
        )


def test_get_leaderboard_without_player_returns_top_players(song, player, rival1, rival2, rival3, top_scores):
    leaderboard = song.get_leaderboard(num_entries=2)

    assert len(leaderboard) == 2

    assert leaderboard[0]["rank"] == 1
    assert leaderboard[0]["name"] == "T1"
    assert leaderboard[0]["score"] == 9900
    assert leaderboard[0]["isSelf"] is False
    assert leaderboard[0]["isRival"] is False
    assert leaderboard[0]["isFail"] is False
    assert leaderboard[0]["machineTag"] == "T1"

    assert leaderboard[1]["rank"] == 2
    assert leaderboard[1]["name"] == "T2"
    assert leaderboard[1]["score"] == 9800
    assert leaderboard[1]["isSelf"] is False
    assert leaderboard[1]["isRival"] is False
    assert leaderboard[1]["isFail"] is False
    assert leaderboard[1]["machineTag"] == "T2"


def test_get_leaderboard_returns_up_to_num_entries(song, player, top_scores):
    leaderboard = song.get_leaderboard(num_entries=30)

    assert len(leaderboard) == 21


def test_player_has_one_top_score_for_a_song(song, player):
    score = player.scores.first()
    assert score.is_top is True

    new_low_score = player.scores.create(
        song=song,
        score=2000,
        comment="M400, OtherMod",
        profile_name="player profile",
    )
    assert new_low_score.is_top is False

    new_top_score = player.scores.create(
        song=song,
        score=8000,
        comment="M400, OtherMod",
        profile_name="player profile",
    )
    assert new_top_score.is_top is True

    score.refresh_from_db()
    assert score.is_top is False


def test_get_leaderboard_when_players_have_multiple_scores(song, player):
    player.scores.create(
        song=song,
        score=8888,
        comment="M320, BETTER ONE",
        profile_name="player profile",
    )

    leaderboard = song.get_leaderboard(num_entries=2)

    assert len(leaderboard) == 1

    assert leaderboard[0]["score"] == 8888


def test_get_leaderboard_given_player_returns_leaderboard_with_their_score_and_up_to_3_rivals(
    song, player, top_scores, rival1, rival2, rival3, rival4
):
    leaderboard = song.get_leaderboard(num_entries=13, player=player)

    assert len(leaderboard) == 13

    for i in range(9):
        assert leaderboard[i]["rank"] == i + 1

    assert leaderboard[9]["name"] == "RIV3"
    assert leaderboard[9]["rank"] == 21
    assert leaderboard[9]["score"] == 7700
    assert leaderboard[9]["isRival"] is True
    assert leaderboard[9]["isSelf"] is False

    assert leaderboard[10]["name"] == "RIV2"
    assert leaderboard[10]["rank"] == 22
    assert leaderboard[10]["score"] == 7588
    assert leaderboard[10]["isRival"] is True
    assert leaderboard[10]["isSelf"] is False

    assert leaderboard[11]["name"] == "RIV4"
    assert leaderboard[11]["rank"] == 23
    assert leaderboard[11]["score"] == 7300
    assert leaderboard[11]["isRival"] is True
    assert leaderboard[11]["isSelf"] is False

    assert leaderboard[12]["name"] == "PL"
    assert leaderboard[12]["rank"] == 24
    assert leaderboard[12]["score"] == 6442
    assert leaderboard[12]["isRival"] is False
    assert leaderboard[12]["isSelf"] is True


def test_player_can_have_more_than_3_rivals(song, player, rival1, rival2, rival3, rival4):
    assert player.rivals.count() == 4
    assert {x.machine_tag for x in player.rivals.all()} == {"RIV1", "RIV2", "RIV3", "RIV4"}


def test_player_cant_be_their_own_rival(song, player):
    assert player.rivals.count() == 0

    with pytest.raises(ValidationError):
        with transaction.atomic():
            player.rivals.add(player)
            player.save()

    player.refresh_from_db()
    assert player.rivals.count() == 0


def test_get_leaderboard_when_entries_would_duplicate(song, player, rival1, rival2, rival3):
    leaderboard = song.get_leaderboard(num_entries=10, player=player)

    assert leaderboard[0]["name"] == "RIV3"
    assert leaderboard[0]["rank"] == 1
    assert leaderboard[0]["score"] == 7700
    assert leaderboard[0]["isRival"] is True
    assert leaderboard[0]["isSelf"] is False

    assert leaderboard[1]["name"] == "RIV2"
    assert leaderboard[1]["rank"] == 2
    assert leaderboard[1]["score"] == 7588
    assert leaderboard[1]["isRival"] is True
    assert leaderboard[1]["isSelf"] is False

    assert leaderboard[2]["name"] == "PL"
    assert leaderboard[2]["rank"] == 3
    assert leaderboard[2]["score"] == 6442
    assert leaderboard[2]["isRival"] is False
    assert leaderboard[2]["isSelf"] is True

    assert leaderboard[3]["name"] == "RIV1"
    assert leaderboard[3]["rank"] == 4
    assert leaderboard[3]["score"] == 4553
    assert leaderboard[3]["isRival"] is True
    assert leaderboard[3]["isSelf"] is False

    assert len(leaderboard) == 4


def test_get_leaderboard_top_when_player_is_provided(song, player, rival3):
    leaderboard = song.get_leaderboard(num_entries=10, player=rival3)

    assert leaderboard[0]["name"] == "RIV3"
    assert leaderboard[0]["rank"] == 1
    assert leaderboard[0]["score"] == 7700
    assert leaderboard[0]["isRival"] is False
    assert leaderboard[0]["isSelf"] is True

    assert leaderboard[1]["name"] == "PL"
    assert leaderboard[1]["rank"] == 2
    assert leaderboard[1]["score"] == 6442
    assert leaderboard[1]["isRival"] is False
    assert leaderboard[1]["isSelf"] is False


def test_get_leaderboard_when_there_are_multiple_songs(song, other_song, player, rival3):
    leaderboard = song.get_leaderboard(num_entries=10, player=rival3)

    assert leaderboard[0]["name"] == "RIV3"
    assert leaderboard[0]["rank"] == 1
    assert leaderboard[0]["score"] == 7700
    assert leaderboard[0]["isRival"] is False
    assert leaderboard[0]["isSelf"] is True

    assert leaderboard[1]["name"] == "PL"
    assert leaderboard[1]["rank"] == 2
    assert leaderboard[1]["score"] == 6442
    assert leaderboard[1]["isRival"] is False
    assert leaderboard[1]["isSelf"] is False
