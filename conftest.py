import pytest
from django.core.management import call_command

from boogiestats.boogie_api.models import Player, Song


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass


@pytest.fixture(scope="session", autouse=True)
def collect_static_files():
    call_command("collectstatic", "--noinput")


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
        itg_score=6442,
        comment="M400, OtherMod",
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
    p.scores.create(
        song=other_song,
        itg_score=6666,
        comment="M400, OtherMod",
        rate=100,
        judgments={
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
    )
    return p


@pytest.fixture
def rival1(player, song):
    rival = Player.objects.create(gs_api_key="rival1key", machine_tag="RIV1")
    rival.scores.create(
        song=song,
        itg_score=4553,
        comment="C500",
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
    player.rivals.add(rival)
    player.save()
    return rival
