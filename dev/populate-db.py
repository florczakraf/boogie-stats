#!/usr/bin/env python3
# flake8: noqa

import django

django.setup()

import json
import sys
from pathlib import Path
from random import randint
from uuid import uuid4

from django.conf import settings

from boogiestats.boogie_api.models import Song, Score, Player

if settings.BS_CHART_DB_PATH:

    def hash_generator():
        jsons = Path(settings.BS_CHART_DB_PATH).rglob("*.json")
        for json_path in jsons:
            try:
                yield json.loads(json_path.read_bytes().decode("utf8", errors="replace"))["hash"]
            except json.decoder.JSONDecodeError as e:
                print(f"{json_path}: {e}", file=sys.stderr)

else:
    print("Consider providing `BS_CHART_DB_PATH` in django settings for a better experience.", file=sys.stderr)

    def hash_generator():
        while True:
            yield uuid4().hex[:16]


PLAYERS = 500
SONGS = 5_000
PLAYERS_PER_SONG = 3  # there's a rand (this, this + 2) later for some variety
SCORES_PER_SONG_PER_PLAYER = 4  # there's a rand (this, this + 2) later for some variety


print("Creating players...")
# bulk create doesn't work here because there's also a related User that has to be created, `create` takes care of that
for i in range(PLAYERS):
    Player.objects.create(gs_api_key=f"player{i}", machine_tag=f"{i}")
print(f"Created {PLAYERS} players")

print("Creating songs...")
hashes = hash_generator()
Song.objects.bulk_create([Song(hash=next(hashes), gs_ranked=bool(randint(0, 1))) for _ in range(SONGS)])
print(f"Created {SONGS} songs")

print("Creating scores...")
for i, song in enumerate(Song.objects.all()):
    players = Player.objects.all().order_by("?")[: randint(PLAYERS_PER_SONG, PLAYERS_PER_SONG + 2)]
    for player in players:
        song.scores.bulk_create(
            [
                Score(
                    song=song,
                    player=player,
                    score=randint(6_000, 10_000),
                    is_itg_top=False,
                    comment="foo",
                    used_cmod=False,
                    has_judgments=True,
                    fantastics=123,
                    greats=77,
                    total_steps=200,
                )
                for _ in range(randint(SCORES_PER_SONG_PER_PLAYER, SCORES_PER_SONG_PER_PLAYER + 2))
            ]
        )
        score = song.scores.filter(player=player).order_by("-itg_score").first()
        score.is_itg_top = True
        score.save()

        score = song.scores.filter(player=player).order_by("-ex_score").first()
        score.is_ex_top = True
        score.save()

    if i % (SONGS // 100) == 0:
        print(".", end="", flush=True)
print(f"Created {Score.objects.count()} scores")


# fixup stuff that would normally be done on score creation

print("Fixing latest scores for players...")
for player in Player.objects.all():
    player.latest_score = player.scores.order_by("-submission_date").first()
    player.save()

print("Fixing ITG highscores for songs...")
for song in Song.objects.all():
    highscore = song.scores.filter(is_itg_top=True).order_by("-itg_score", "submission_date").first()
    song.itg_highscore = highscore
    song.save()

print("Fixing EX highscores for songs...")
for song in Song.objects.all():
    highscore = song.scores.filter(is_ex_top=True).order_by("-ex_score", "submission_date").first()
    song.ex_highscore = highscore
    song.save()

print("Done")
