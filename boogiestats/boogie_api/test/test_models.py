import pytest
from django.core.exceptions import ValidationError
from django.db import transaction

from boogiestats.boogie_api.models import Song, Player


@pytest.fixture
def song_without_scores():
    return Song.objects.create(hash="yetanothersong")


@pytest.fixture
def rival2(player, song):
    rival = Player.objects.create(gs_api_key="rival2key", machine_tag="RIV2")
    rival.scores.create(
        song=song,
        itg_score=7588,
        comment="C200",
        rate=100,
        judgments={
            "excellent": 90,
            "fantastic": 0,
            "fantasticPlus": 0,
            "great": 2,
            "holdsHeld": 6,
            "minesHit": 0,
            "miss": 0,
            "rollsHeld": 3,
            "totalHolds": 6,
            "totalMines": 5,
            "totalRolls": 3,
            "totalSteps": 92,
        },
    )
    player.rivals.add(rival)
    player.save()
    return rival


@pytest.fixture
def rival3(player, song):
    rival = Player.objects.create(gs_api_key="rival3key", machine_tag="RIV3")
    rival.scores.create(
        song=song,
        itg_score=7700,
        comment="M550",
        rate=100,
        judgments={
            "excellent": 92,
            "fantastic": 0,
            "fantasticPlus": 0,
            "great": 0,
            "holdsHeld": 6,
            "minesHit": 0,
            "miss": 0,
            "rollsHeld": 3,
            "totalHolds": 6,
            "totalMines": 5,
            "totalRolls": 3,
            "totalSteps": 92,
        },
    )
    player.rivals.add(rival)
    player.save()
    return rival


@pytest.fixture
def rival4(player, song):
    rival = Player.objects.create(gs_api_key="rival4key", machine_tag="RIV4")
    rival.scores.create(
        song=song,
        itg_score=7300,
        comment="M550",
        rate=105,
        judgments={
            "excellent": 88,
            "fantastic": 0,
            "fantasticPlus": 0,
            "great": 4,
            "holdsHeld": 6,
            "minesHit": 0,
            "miss": 0,
            "rollsHeld": 3,
            "totalHolds": 6,
            "totalMines": 5,
            "totalRolls": 3,
            "totalSteps": 92,
        },
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
            itg_score=10_000 - i * 100,
            comment=f"M420, TOP{i}",
            rate=100,
            judgments={
                "excellent": 0,
                "fantastic": i,
                "fantasticPlus": 92 - i,
                "great": 0,
                "holdsHeld": 6,
                "minesHit": 0,
                "miss": 0,
                "rollsHeld": 3,
                "totalHolds": 6,
                "totalMines": 5,
                "totalRolls": 3,
                "totalSteps": 92,
            },
        )


@pytest.fixture
def tied_scores(song):
    for i in range(1, 11):
        p = Player.objects.create(gs_api_key=f"top{i}key", machine_tag=f"T{i}")
        p.scores.create(
            song=song,
            itg_score=10_000,
            comment=f"M420, TOP{i}",
            rate=100,
            judgments={
                "excellent": 0,
                "fantastic": 0,
                "fantasticPlus": 92,
                "great": 0,
                "holdsHeld": 6,
                "minesHit": 0,
                "miss": 0,
                "rollsHeld": 3,
                "totalHolds": 6,
                "totalMines": 5,
                "totalRolls": 3,
                "totalSteps": 92,
            },
        )


def test_get_leaderboard_without_player_returns_top_players_itg_scores(
    song, player, rival1, rival2, rival3, top_scores
):
    leaderboard = song.get_leaderboard(num_entries=2, score_type="itg")

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


def test_get_leaderboard_with_tied_players_should_respect_dates(song, player, rival1, rival2, rival3, tied_scores):
    leaderboard = song.get_leaderboard(num_entries=13, score_type="itg")

    assert len(leaderboard) == 13

    for i in range(1, 11):
        assert leaderboard[i - 1]["rank"] == i
        assert leaderboard[i - 1]["name"] == f"T{i}"
        assert leaderboard[i - 1]["score"] == 10_000
        assert leaderboard[i - 1]["isSelf"] is False
        assert leaderboard[i - 1]["isRival"] is False
        assert leaderboard[i - 1]["isFail"] is False
        assert leaderboard[i - 1]["machineTag"] == f"T{i}"

    assert leaderboard[10]["rank"] == 11
    assert leaderboard[11]["rank"] == 12


def test_get_leaderboard_returns_up_to_num_entries(song, player, top_scores):
    leaderboard = song.get_leaderboard(num_entries=30, score_type="itg")

    assert len(leaderboard) == 21


def test_player_has_one_top_score_for_a_song(song, player):
    score = player.scores.first()
    assert score.is_itg_top is True
    assert score.is_ex_top is True

    new_low_itg_top_ex_score = player.scores.create(
        song=song,
        itg_score=2000,
        comment="M400, OtherMod",
        rate=100,
        judgments={
            "excellent": 0,
            "fantastic": 0,
            "fantasticPlus": 92,
            "great": 0,
            "holdsHeld": 6,
            "minesHit": 0,
            "miss": 0,
            "rollsHeld": 3,
            "totalHolds": 6,
            "totalMines": 5,
            "totalRolls": 3,
            "totalSteps": 92,
        },
    )
    assert new_low_itg_top_ex_score.is_itg_top is False
    assert new_low_itg_top_ex_score.is_ex_top is True

    new_top_itg_low_ex_score = player.scores.create(
        song=song,
        itg_score=8000,
        comment="M400, OtherMod",
        rate=100,
        judgments={
            "excellent": 0,
            "fantastic": 0,
            "fantasticPlus": 0,
            "great": 92,
            "holdsHeld": 6,
            "minesHit": 0,
            "miss": 0,
            "rollsHeld": 3,
            "totalHolds": 6,
            "totalMines": 5,
            "totalRolls": 3,
            "totalSteps": 92,
        },
    )
    assert new_top_itg_low_ex_score.is_itg_top is True
    assert new_top_itg_low_ex_score.is_ex_top is False

    score.refresh_from_db()
    assert score.is_itg_top is False
    assert score.is_ex_top is False


def test_get_leaderboard_when_players_have_multiple_scores(song, player):
    player.scores.create(
        song=song,
        itg_score=8888,
        comment="M320, BETTER ONE",
        rate=100,
    )

    leaderboard = song.get_leaderboard(num_entries=2, score_type="itg")

    assert len(leaderboard) == 1

    assert leaderboard[0]["score"] == 8888


@pytest.mark.parametrize("score_type", ["itg", "ex"])
def test_get_leaderboard_given_player_returns_leaderboard_with_their_score_and_up_to_3_rivals(
    song, player, top_scores, rival1, rival2, rival3, rival4, score_type
):
    leaderboard = song.get_leaderboard(num_entries=13, player=player, score_type=score_type)

    assert len(leaderboard) == 13

    for i in range(9):
        assert leaderboard[i]["rank"] == i + 1

    assert leaderboard[9]["name"] == "RIV3"
    assert leaderboard[9]["rank"] == 21
    assert leaderboard[9]["score"] == (7700 if score_type == "itg" else 5830)
    assert leaderboard[9]["isRival"] is True
    assert leaderboard[9]["isSelf"] is False

    assert leaderboard[10]["name"] == "RIV2"
    assert leaderboard[10]["rank"] == 22
    assert leaderboard[10]["score"] == (7588 if score_type == "itg" else 5770)
    assert leaderboard[10]["isRival"] is True
    assert leaderboard[10]["isSelf"] is False

    assert leaderboard[11]["name"] == "RIV4"
    assert leaderboard[11]["rank"] == 23
    assert leaderboard[11]["score"] == (7300 if score_type == "itg" else 5709)
    assert leaderboard[11]["isRival"] is True
    assert leaderboard[11]["isSelf"] is False

    assert leaderboard[12]["name"] == "PL"
    assert leaderboard[12]["rank"] == 24
    assert leaderboard[12]["score"] == (6442 if score_type == "itg" else 4441)
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
    leaderboard = song.get_leaderboard(num_entries=10, score_type="itg", player=player)

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
    leaderboard = song.get_leaderboard(num_entries=10, score_type="itg", player=rival3)

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
    leaderboard = song.get_leaderboard(num_entries=10, score_type="itg", player=rival3)

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


def test_highscore_updates(player, rival1, song):
    assert song.scores.order_by("-itg_score", "submission_date").first() == song.itg_highscore
    assert song.scores.order_by("-ex_score", "submission_date").first() == song.ex_highscore
    assert song.itg_highscore.itg_score == 6442
    assert song.ex_highscore.ex_score == 4441
    previous_itg_highscore = song.itg_highscore
    previous_ex_highscore = song.ex_highscore

    equal_score = song.scores.create(
        player=player,
        itg_score=6442,
        comment="foo",
        rate=100,
        judgments={
            "excellent": 46,
            "fantastic": 0,
            "fantasticPlus": 0,
            "great": 46,
            "holdsHeld": 6,
            "minesHit": 0,
            "miss": 0,
            "rollsHeld": 3,
            "totalHolds": 6,
            "totalMines": 5,
            "totalRolls": 3,
            "totalSteps": 92,
        },
    )
    song.refresh_from_db()

    assert song.itg_highscore == previous_itg_highscore
    assert song.ex_highscore == previous_ex_highscore
    assert song.scores.order_by("-itg_score", "submission_date").all()[1] == equal_score
    assert song.scores.order_by("-ex_score", "submission_date").all()[1] == equal_score

    better_score = song.scores.create(
        player=player,
        itg_score=6542,
        comment="foo",
        rate=100,
        judgments={
            "excellent": 92,
            "fantastic": 0,
            "fantasticPlus": 0,
            "great": 0,
            "holdsHeld": 6,
            "minesHit": 0,
            "miss": 0,
            "rollsHeld": 3,
            "totalHolds": 6,
            "totalMines": 5,
            "totalRolls": 3,
            "totalSteps": 92,
        },
    )
    song.refresh_from_db()

    assert song.itg_highscore != previous_itg_highscore
    assert song.itg_highscore == better_score
    assert song.itg_highscore.itg_score == 6542
    assert song.ex_highscore != previous_ex_highscore
    assert song.ex_highscore == better_score
    assert song.ex_highscore.ex_score == 5830
    assert better_score.itg_highscore_for.first() == song
    assert better_score.ex_highscore_for.first() == song


def test_first_score_for_a_song_is_itg_and_ex_top_for_a_player(player):
    new_song = Song.objects.create(hash="new song")
    score = player.scores.create(song=new_song, itg_score=5050, comment="55g", rate=100)

    assert score.is_itg_top is True
    assert score.is_ex_top is True


def test_better_itg_score_handles_is_itg_top_for_new_and_previous_top(player, song):
    previous_score = song.scores.filter(player=player).first()

    assert previous_score.is_itg_top is True
    assert previous_score.is_ex_top is True

    better_itg_score = player.scores.create(
        song=song,
        itg_score=10_000,
        comment="",
        rate=100,
        judgments={
            "great": 92,
            "totalSteps": 92,
        },
    )

    previous_score.refresh_from_db()
    assert better_itg_score.is_itg_top is True
    assert better_itg_score.is_ex_top is False
    assert previous_score.is_itg_top is False
    assert previous_score.is_ex_top is True


def test_better_ex_score_handles_is_ex_top_for_new_and_previous_top(player, song):
    previous_score = song.scores.filter(player=player).first()

    assert previous_score.is_itg_top is True
    assert previous_score.is_ex_top is True

    better_ex_score = player.scores.create(
        song=song,
        itg_score=2_000,
        comment="",
        rate=100,
        judgments={
            "fantasticPlus": 92,
            "totalSteps": 92,
        },
    )

    previous_score.refresh_from_db()
    assert better_ex_score.is_itg_top is False
    assert better_ex_score.is_ex_top is True
    assert previous_score.is_itg_top is True
    assert previous_score.is_ex_top is False


@pytest.mark.parametrize(
    ("used_cmod", "comment", "expected_used_cmod"),
    [
        (None, "", False),
        (None, "foo, bar, baz", False),
        (None, "foo, bar, baz", False),
        (None, "foo, C324, bar", True),
        (True, "foo, bar", True),
        (False, "foo, bar", False),
        (False, "foo, C454, bar", False),  # used_cmod takes precedence
    ],
)
def test_score_create_used_cmod(player, song, used_cmod, comment, expected_used_cmod):
    score = player.scores.create(song=song, itg_score=5555, comment=comment, rate=100, used_cmod=used_cmod)

    assert score.used_cmod is expected_used_cmod


def test_score_create_sets_songs_highscore(player):
    new_song = Song.objects.create(hash="new song")
    assert new_song.itg_highscore is None
    assert new_song.ex_highscore is None

    score = player.scores.create(song=new_song, itg_score=10_000, comment="comment", rate=100)

    new_song.refresh_from_db()
    assert new_song.itg_highscore == score
    assert new_song.ex_highscore == score


def test_score_create_updates_songs_itg_highscore(player, song):
    previous_itg_highscore = song.itg_highscore
    previous_ex_highscore = song.ex_highscore

    score = player.scores.create(song=song, itg_score=10_000, comment="comment", rate=100)

    song.refresh_from_db()
    assert previous_itg_highscore != score
    assert song.itg_highscore == score
    assert song.ex_highscore == previous_ex_highscore


def test_score_create_updates_songs_ex_highscore(player, song):
    previous_itg_highscore = song.itg_highscore
    previous_ex_highscore = song.ex_highscore

    score = player.scores.create(
        song=song,
        itg_score=1_000,
        comment="comment",
        rate=100,
        judgments={
            "fantasticPlus": 92,
            "totalSteps": 92,
        },
    )

    song.refresh_from_db()
    assert previous_ex_highscore != score
    assert song.ex_highscore == score
    assert song.itg_highscore == previous_itg_highscore


def test_score_create_sets_players_latest_score(song):
    new_player = Player.objects.create(gs_api_key="new_player", machine_tag="PLAY")
    assert new_player.latest_score is None

    score = new_player.scores.create(song=song, itg_score=5900, comment="comment", rate=100)

    new_player.refresh_from_db()
    assert new_player.latest_score == score


def test_score_create_updates_players_latest_score(player, song):
    previous_latest_score = player.latest_score

    score = player.scores.create(song=song, itg_score=5900, comment="comment", rate=100)

    player.refresh_from_db()
    assert previous_latest_score != player.latest_score
    assert player.latest_score == score


def test_score_create_increases_players_num_scores(player, song):
    previous_num_scores = player.num_scores

    player.scores.create(song=song, itg_score=5900, comment="comment", rate=100)

    player.refresh_from_db()
    assert previous_num_scores != player.latest_score
    assert player.num_scores == previous_num_scores + 1


def test_score_create_updates_songs_number_of_players(player, rival1, song_without_scores):
    player.scores.create(song=song_without_scores, itg_score=5900, comment="comment", rate=100)

    song_without_scores.refresh_from_db()
    assert song_without_scores.number_of_players == 1

    rival1.scores.create(song=song_without_scores, itg_score=5900, comment="comment", rate=100)

    song_without_scores.refresh_from_db()
    assert song_without_scores.number_of_players == 2


def test_score_create_updates_songs_number_of_scores(player, rival1, song_without_scores):
    player.scores.create(song=song_without_scores, itg_score=5900, comment="comment", rate=100)

    song_without_scores.refresh_from_db()
    assert song_without_scores.number_of_scores == 1

    rival1.scores.create(song=song_without_scores, itg_score=5900, comment="comment", rate=100)
    player.scores.create(song=song_without_scores, itg_score=5900, comment="comment", rate=100)

    song_without_scores.refresh_from_db()
    assert song_without_scores.number_of_scores == 3


@pytest.mark.parametrize(
    ("itg_score", "stars_field"),
    [
        (9700, "one_star"),
        (9810, "two_stars"),
        (9950, "three_stars"),
        (10_000, "four_stars"),
    ],
)
def test_score_create_adds_players_stars(player, song_without_scores, itg_score, stars_field):
    start_stars = getattr(player, stars_field)

    player.scores.create(song=song_without_scores, itg_score=itg_score, comment="comment", rate=100)

    player.refresh_from_db()
    assert getattr(player, stars_field) == start_stars + 1

    # second one shouldn't increase the counter
    player.scores.create(song=song_without_scores, itg_score=itg_score, comment="comment", rate=100)

    player.refresh_from_db()
    assert getattr(player, stars_field) == start_stars + 1


def test_score_create_decreases_player_stars(player, song_without_scores):
    assert player.five_stars == player.four_stars == player.three_stars == player.two_stars == player.one_star == 0

    # score below star thresholds
    player.scores.create(song=song_without_scores, itg_score=7000, comment="comment", rate=100)

    player.refresh_from_db()
    assert player.five_stars == player.four_stars == player.three_stars == player.two_stars == player.one_star == 0

    # improved to one star
    player.scores.create(song=song_without_scores, itg_score=9600, comment="comment", rate=100)

    player.refresh_from_db()
    assert player.five_stars == player.four_stars == player.three_stars == player.two_stars == 0
    assert player.one_star == 1

    # improved to two stars
    player.scores.create(song=song_without_scores, itg_score=9800, comment="comment", rate=100)

    player.refresh_from_db()
    assert player.five_stars == player.four_stars == player.three_stars == player.one_star == 0
    assert player.two_stars == 1

    # improved to three stars
    player.scores.create(song=song_without_scores, itg_score=9900, comment="comment", rate=100)

    player.refresh_from_db()
    assert player.five_stars == player.four_stars == player.two_stars == player.one_star == 0
    assert player.three_stars == 1

    # improved to four stars
    player.scores.create(song=song_without_scores, itg_score=10_000, comment="comment", rate=100)

    player.refresh_from_db()
    assert player.five_stars == player.three_stars == player.two_stars == player.one_star == 0
    assert player.four_stars == 1


def test_score_create_updates_players_quints_on_new_quints(player, song_without_scores):
    start_quints = player.five_stars

    player.scores.create(
        song=song_without_scores,
        itg_score=10_000,
        judgments={"fantasticPlus": 10, "totalSteps": 10},
        comment="comment",
        rate=100,
    )

    player.refresh_from_db()
    assert player.five_stars == start_quints + 1

    # create second quint
    player.scores.create(
        song=song_without_scores,
        itg_score=10_000,
        judgments={"fantasticPlus": 10, "totalSteps": 10},
        comment="comment",
        rate=100,
    )
    player.refresh_from_db()
    assert player.five_stars == start_quints + 1  # it shouldn't increase
