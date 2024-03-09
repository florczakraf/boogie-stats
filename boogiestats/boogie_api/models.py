import json
import math
from hashlib import sha256
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Count
from django.db.models.signals import m2m_changed
from django.utils.timezone import now
from django.utils.functional import cached_property
from redis import Redis

from boogiestats.boogie_api.managers import ScoreManager, PlayerManager
from boogiestats.boogie_api.utils import get_redis
from boogiestats.boogiestats.exceptions import Managed404Error

MAX_LEADERBOARD_RIVALS = 3
MAX_LEADERBOARD_ENTRIES = 50


class LeaderboardSource(models.IntegerChoices):
    BS = 1, "BoogieStats"
    GS = 2, "GrooveStats"


def make_leaderboard_entry(rank, score, score_type, is_rival=False, is_self=False):
    if score_type not in ("itg", "ex"):
        raise ValueError(f"Unsupported score type: {score_type}")

    return {
        "rank": rank,
        "name": score.player.name or score.player.machine_tag,  # use name if available
        "score": getattr(score, f"{score_type}_score"),
        "date": score.submission_date.strftime("%Y-%m-%d %H:%M:%S"),
        "isSelf": is_self,
        "isRival": is_rival,
        "isFail": False,
        "machineTag": score.player.machine_tag,
    }


class Song(models.Model):
    hash = models.CharField(max_length=16, primary_key=True, db_index=True)  # V3 GrooveStats hash 16 a-f0-9
    gs_ranked = models.BooleanField(default=False)
    itg_highscore = models.ForeignKey(
        "Score", null=True, blank=True, on_delete=models.deletion.SET_NULL, related_name="itg_highscore_for"
    )
    ex_highscore = models.ForeignKey(
        "Score", null=True, blank=True, on_delete=models.deletion.SET_NULL, related_name="ex_highscore_for"
    )
    number_of_scores = models.PositiveIntegerField(default=0, db_index=True)
    number_of_players = models.PositiveIntegerField(default=0, db_index=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_leaderboard(self, num_entries, score_type, player=None):
        num_entries = min(MAX_LEADERBOARD_ENTRIES, num_entries)

        scores = []
        used_score_pks = []

        if player:
            rank, score = self.get_highscore(player, score_type)
            if rank:
                scores.append((score, make_leaderboard_entry(rank, score, score_type, is_self=True)))
                used_score_pks.append(score.pk)

            for rank, score in self.get_rival_highscores(player, score_type):
                scores.append((score, make_leaderboard_entry(rank, score, score_type, is_rival=True)))
                used_score_pks.append(score.pk)

        remaining_scores = max(0, num_entries - len(scores))

        top_scores = (
            self.scores.filter(**{f"is_{score_type}_top": True})
            .exclude(pk__in=used_score_pks)
            .order_by(f"-{score_type}_score", "submission_date", "id")[:remaining_scores]
        )

        for score in top_scores:
            rank = Score.rank(score, score_type)
            scores.append((score, make_leaderboard_entry(rank, score, score_type)))

        sorted_scores = sorted(
            scores,
            key=lambda x: (-getattr(x[0], f"{score_type}_score"), x[0].submission_date, x[0].id),
        )

        return [x[1] for x in sorted_scores]

    def get_highscore(self, player, score_type) -> (int, "Score"):
        try:
            highscore = self.scores.get(player=player, **{f"is_{score_type}_top": True})
        except Score.DoesNotExist:
            return None, None

        return Score.rank(highscore, score_type), highscore

    def get_rival_highscores(self, player, score_type) -> [(int, "Score")]:
        scores = (
            self.scores.filter(**{f"is_{score_type}_top": True, "player__in": player.rivals.all()})
            .order_by(f"-{score_type}_score", "submission_date", "id")[:MAX_LEADERBOARD_RIVALS]
            .all()
        )

        return [(Score.rank(score, score_type), score) for score in scores]

    @cached_property
    def chart_info(self):
        """Chart info based on an external (optional) chart database"""
        if settings.BS_CHART_DB_PATH is not None:
            path = Path(settings.BS_CHART_DB_PATH) / self.hash[:2] / f"{self.hash[2:]}.json"
            if path.exists():
                return json.loads(path.read_bytes().decode("utf8", errors="replace"))  # some charts have weird bytes
        return None

    @property
    def display_name(self):
        final_name = self.hash

        if info := self.chart_info:
            artist = info["artisttranslit"] or info["artist"]
            title = info["titletranslit"] or info["title"]

            subtitle = info["subtitletranslit"] or info["subtitle"]
            if subtitle:
                if not (subtitle.startswith("(") and subtitle.endswith(")")):  # fix inconsistent braces
                    subtitle = f"({subtitle})"
                subtitle = f" {subtitle}"

            base_display_name = f"{artist} - {title}{subtitle}"
            final_name = base_display_name

            steps_type = info["steps_type"]
            if steps_type != "dance-single":  # don't display dance-single because it's most common chart type
                final_name += f" ({steps_type})"

        return final_name

    @staticmethod
    def get_or_404(*args, **kwargs):
        try:
            return Song.objects.get(*args, **kwargs)
        except Song.DoesNotExist:
            raise Managed404Error("Requested song does not exist.")

    def set_ranked(self, is_ranked):
        if is_ranked and not self.gs_ranked:
            self.gs_ranked = True
            self.save()

    def update_search_cache(self, redis_connection: Optional[Redis] = None) -> bool:
        """Updates song search cache when both redis and song metadata ara available."""

        r = redis_connection or get_redis()
        if not r:
            return False

        chart_info = self.chart_info

        if chart_info is not None:
            chart_info["num_plays"] = self.scores.count()

            fields = (
                "title",
                "titletranslit",
                "subtitle",
                "subtitletranslit",
                "artist",
                "artisttranslit",
                "diff",
                "diff_number",
                "steps_type",
                "pack_name",
                "num_plays",
            )

            r.hset(f"song:{self.hash}", mapping={k: v for k, v in chart_info.items() if k in fields})
            return True

        return False

    def update_number_of_players_and_scores(self):
        annotated_song = (
            Song.objects.filter(hash=self.hash)
            .annotate(num_scores=Count("scores"), num_players=Count("scores__player", distinct=True))
            .first()
        )
        self.number_of_players = annotated_song.num_players
        self.number_of_scores = annotated_song.num_scores

    def __str__(self):
        return f"{self.hash} - {self.display_name}"


class Player(models.Model):
    objects = PlayerManager()

    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)  # to utilize standard auth stuff
    api_key = models.CharField(max_length=64, db_index=True, unique=True)
    machine_tag = models.CharField(max_length=4)
    name = models.CharField(max_length=64, blank=True, null=True)
    rivals = models.ManyToManyField(
        "self", symmetrical=False, blank=True, help_text="Hold ctrl to select/unselect multiple"
    )
    latest_score = models.ForeignKey(
        "Score", null=True, blank=True, on_delete=models.deletion.SET_NULL, related_name="latest_score_for"
    )
    join_date = models.DateTimeField(default=now, db_index=True)
    pull_gs_name_and_tag = models.BooleanField(
        default=True,
        verbose_name="Pull GrooveStats name and tag",
        help_text="Pull name and tag on successful GS-ranked score submission",
    )
    leaderboard_source = models.IntegerField(choices=LeaderboardSource.choices, default=LeaderboardSource.BS)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @staticmethod
    def get_by_gs_api_key(gs_api_key) -> Optional["Player"]:
        api_key = Player.gs_api_key_to_bs_api_key(gs_api_key)
        return Player.objects.filter(api_key=api_key).first()

    @staticmethod
    def gs_api_key_to_bs_api_key(gs_api_key):
        return sha256(gs_api_key[:32].encode("ascii")).hexdigest()

    def __str__(self):
        return f"{self.id} - {self.name} ({self.machine_tag})"

    @staticmethod
    def get_or_404(*args, **kwargs):
        try:
            return Player.objects.get(*args, **kwargs)
        except Player.DoesNotExist:
            raise Managed404Error("Requested player does not exist.")

    def _get_self_entry(self, gs_player):
        leaderboard = gs_player.get("gsLeaderboard", [])
        try:
            self_entry = next(x for x in leaderboard if x["isSelf"])
        except StopIteration:
            self_entry = None

        return self_entry

    def update_name_and_tag(self, gs_player):
        if not self.pull_gs_name_and_tag:
            return

        if self_entry := self._get_self_entry(gs_player):
            # Turns out that at least tag can be unset
            if (name := self_entry.get("name")) is not None:
                self.name = name

            if (machine_tag := self_entry.get("machineTag")) is not None:
                self.machine_tag = machine_tag

            self.save()


def validate_rivals(sender, **kwargs):
    if kwargs["instance"].rivals.filter(api_key=kwargs["instance"].api_key).count() == 1:
        raise ValidationError("You can't be your own rival")


m2m_changed.connect(validate_rivals, sender=Player.rivals.through)


class Score(models.Model):
    objects = ScoreManager()
    MAX_COMMENT_LENGTH = 200
    MAX_SCORE = 10_000
    MAX_RATE = 500

    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="scores")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="scores")
    submission_date = models.DateTimeField(default=now, db_index=True)
    submission_day = models.DateField(default=now, db_index=True)
    itg_score = models.PositiveIntegerField(validators=[MaxValueValidator(MAX_SCORE)], db_index=True)
    ex_score = models.PositiveIntegerField(validators=[MaxValueValidator(MAX_SCORE)], default=0, db_index=True)

    comment = models.CharField(max_length=MAX_COMMENT_LENGTH, blank=True)
    is_itg_top = models.BooleanField(default=True, db_index=True)
    is_ex_top = models.BooleanField(default=False, db_index=True)
    used_cmod = models.BooleanField(default=False)
    rate = models.PositiveIntegerField(default=100, validators=[MaxValueValidator(MAX_RATE)])

    has_judgments = models.BooleanField(default=False)
    misses = models.PositiveIntegerField(default=0)
    way_offs = models.PositiveIntegerField(default=0)
    decents = models.PositiveIntegerField(default=0)
    greats = models.PositiveIntegerField(default=0)
    excellents = models.PositiveIntegerField(default=0)
    fantastics = models.PositiveIntegerField(default=0)
    fantastics_plus = models.PositiveIntegerField(default=0)
    total_steps = models.PositiveIntegerField(default=0)
    total_rolls = models.PositiveIntegerField(default=0)
    total_holds = models.PositiveIntegerField(default=0)
    total_mines = models.PositiveIntegerField(default=0)
    rolls_held = models.PositiveIntegerField(default=0)
    holds_held = models.PositiveIntegerField(default=0)
    mines_hit = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def rank(cls, score, score_type):
        return (
            list(
                cls.objects.filter(
                    song=score.song,
                    **{f"is_{score_type}_top": True, f"{score_type}_score__gte": getattr(score, f"{score_type}_score")},
                )
                .order_by(f"-{score_type}_score", "submission_date", "id")
                .values_list("id", flat=True)
            ).index(score.id)
            + 1
        )

    def calculate_ex(self) -> int:
        if not self.has_judgments:
            return 0

        weights = {
            "fa+": 3.5,
            "fantastics": 3,
            "excellents": 2,
            "greats": 1,
            "held": 1,
            "mine": -1,
        }
        total_possible = self.total_steps * weights["fa+"] + (self.total_holds + self.total_rolls) * weights["held"]
        points = (
            self.fantastics_plus * weights["fa+"]
            + self.fantastics * weights["fantastics"]
            + self.excellents * weights["excellents"]
            + self.greats * weights["greats"]
            + self.rolls_held * weights["held"]
            + self.holds_held * weights["held"]
            + self.mines_hit * weights["mine"]
        )

        try:
            return int(max(0, math.floor(points / total_possible * 10_000)))
        except ZeroDivisionError:
            return 0

    def __str__(self):
        return f"{self.id} - {self.submission_date} - {self.itg_score/100}% - {self.ex_score/100}% EX - {self.song.display_name} - {self.player}"
