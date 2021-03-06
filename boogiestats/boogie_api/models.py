import json
from hashlib import sha256
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import m2m_changed
from django.utils.timezone import now

from boogiestats.boogie_api.managers import ScoreManager, PlayerManager

MAX_RIVALS = 3


def make_leaderboard_entry(rank, score, is_rival=False, is_self=False):
    return {
        "rank": rank,
        "name": score.player.name or score.player.machine_tag,  # use name if available
        "score": score.score,
        "date": score.submission_date.strftime("%Y-%m-%d %H:%M:%S"),
        "isSelf": is_self,
        "isRival": is_rival,
        "isFail": False,
        "machineTag": score.player.machine_tag,
    }


class Song(models.Model):
    hash = models.CharField(max_length=16, primary_key=True, db_index=True)  # V3 GrooveStats hash 16 a-f0-9

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_leaderboard(self, num_entries, player=None):
        assert num_entries < 50

        scores = []
        used_score_pks = []

        if player:
            rank, score = self.get_highscore(player)
            if rank:
                scores.append(make_leaderboard_entry(rank, score, is_self=True))
                used_score_pks.append(score.pk)

            for rival in player.rivals.all():
                rank, score = self.get_highscore(rival)
                if rank:
                    scores.append(make_leaderboard_entry(rank, score, is_rival=True))
                    used_score_pks.append(score.pk)

        remaining_scores = max(0, num_entries - len(scores))

        top_scores = (
            self.scores.filter(is_top=True).exclude(pk__in=used_score_pks).order_by("-score")[:remaining_scores]
        )

        for score in top_scores:
            rank = Score.rank(score)
            scores.append(make_leaderboard_entry(rank, score))

        return sorted(scores, key=lambda x: x["score"], reverse=True)

    def get_highscore(self, player) -> (int, "Score"):
        try:
            highscore = self.scores.get(player=player, is_top=True)
        except Score.DoesNotExist:
            return None, None

        return Score.rank(highscore), highscore

    @property
    def highscore(self):
        return self.scores.filter(is_top=True).order_by("-score", "-submission_date").first()

    @property
    def chart_info(self):
        """Chart info based on an external (optional) chart database"""
        if settings.BS_CHART_DB_PATH is not None:
            path = Path(settings.BS_CHART_DB_PATH) / self.hash[:2] / f"{self.hash[2:]}.json"
            if path.exists():
                return json.loads(path.read_bytes().decode("utf8", errors="replace"))  # some charts have weird bytes
        return None

    @property
    def display_name(self):
        if info := self.chart_info:
            artist = info["artisttranslit"] or info["artist"]
            title = info["titletranslit"] or info["title"]

            subtitle = info["subtitletranslit"] or info["subtitle"]
            if subtitle:
                if not (subtitle.startswith("(") and subtitle.endswith(")")):  # fix inconsistent braces
                    subtitle = f"({subtitle})"
                subtitle = f" {subtitle}"

            diff = info["diff"]
            steps_type = info["steps_type"]
            return f"{artist} - {title}{subtitle} [{diff}, {steps_type}]"

        return self.hash


class Player(models.Model):
    objects = PlayerManager()

    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)  # to utilize standard auth stuff
    api_key = models.CharField(max_length=64, db_index=True, unique=True)
    machine_tag = models.CharField(max_length=4)
    name = models.CharField(max_length=64, blank=True, null=True)
    rivals = models.ManyToManyField(
        "self", symmetrical=False, blank=True, help_text="Hold ctrl to select/unselect multiple"
    )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @staticmethod
    def get_by_gs_api_key(gs_api_key):
        api_key = Player.gs_api_key_to_bs_api_key(gs_api_key)
        return Player.objects.filter(api_key=api_key).first()

    @staticmethod
    def gs_api_key_to_bs_api_key(gs_api_key):
        return sha256(gs_api_key[:32].encode("ascii")).hexdigest()

    def __str__(self):
        return f"{self.id} - {self.name} ({self.machine_tag})"


def validate_rivals(sender, **kwargs):
    if kwargs["instance"].rivals.count() > MAX_RIVALS:
        raise ValidationError(f"A Player can have at most {MAX_RIVALS} rivals.")


m2m_changed.connect(validate_rivals, sender=Player.rivals.through)


class Score(models.Model):
    objects = ScoreManager()

    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="scores")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="scores")
    submission_date = models.DateTimeField(default=now)
    score = models.IntegerField()
    comment = models.CharField(max_length=200)
    profile_name = models.CharField(max_length=50, blank=True, null=True)
    is_top = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def rank(cls, score):
        return cls.objects.filter(song=score.song, is_top=True, score__gt=score.score).count() + 1
