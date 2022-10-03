import uuid
from typing import Optional, TYPE_CHECKING

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction

if TYPE_CHECKING:
    from boogiestats.boogie_api.models import Song, Player

JUDGMENTS_MAP = {
    "miss": "misses",
    "wayOff": "way_offs",
    "decent": "decents",
    "great": "greats",
    "excellent": "excellents",
    "fantastic": "fantastics",
    "fantasticPlus": "fantastics_plus",
    "totalSteps": "total_steps",
    "totalRolls": "total_rolls",
    "totalHolds": "total_holds",
    "totalMines": "total_mines",
    "rollsHeld": "rolls_held",
    "holdsHeld": "holds_held",
    "minesHit": "mines_hit",
}


class ScoreManager(models.Manager):
    @transaction.atomic
    def create(
        self,
        song: "Song",
        player: "Player",
        score: int,
        comment: str,
        rate: int,
        used_cmod: Optional[bool] = None,
        judgments: Optional = None,
    ):

        used_cmod = self._handle_used_cmod(used_cmod, comment)
        new_is_top = self._handle_is_top(song, player, score)

        score_object = self.model(
            song=song,
            player=player,
            score=score,
            comment=comment,
            is_top=new_is_top,
            rate=rate,
            used_cmod=used_cmod,
        )

        self._handle_judgments(score_object, judgments)

        score_object.save()

        self._handle_highscore_update(score_object, song)
        self._handle_latest_score_update(score_object, player)

        return score_object

    def _handle_used_cmod(self, used_cmod, comment):
        if used_cmod is None:  # fallback to comment parsing
            # Just a trivial check because I don't really care about false-positives much,
            # update your client if you wish to have accurate stats ¯\_(ツ)_/¯
            used_cmod = "C" in comment

        return used_cmod

    def _handle_is_top(self, song, player, score):
        new_is_top = False

        try:
            previous_top = song.scores.get(player=player, is_top=True)
        except ObjectDoesNotExist:
            previous_top = None
            new_is_top = True

        if previous_top and previous_top.score < score:
            new_is_top = True
            previous_top.is_top = False
            previous_top.save()

        return new_is_top

    def _handle_judgments(self, score_object, judgments):
        if judgments is not None:
            score_object.has_judgments = True
            for src, dst in JUDGMENTS_MAP.items():
                setattr(score_object, dst, judgments.get(src, 0))

    def _handle_highscore_update(self, score_object, song):
        if not song.highscore or score_object.score > song.highscore.score:
            song.highscore = score_object
            song.save()

    def _handle_latest_score_update(self, score_object, player):
        player.latest_score = score_object
        player.save()


class PlayerManager(models.Manager):
    def create(self, gs_api_key, machine_tag, **kwargs):
        user = User.objects.create_user(username=uuid.uuid4().hex)
        kwargs.setdefault("name", machine_tag)
        player = self.model(
            user=user,
            api_key=self.model.gs_api_key_to_bs_api_key(gs_api_key),
            machine_tag=machine_tag,
            **kwargs,
        )
        player.save()

        return player
