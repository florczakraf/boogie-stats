import uuid
from typing import TYPE_CHECKING, Optional

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction

from boogiestats.boogie_api.utils import score_to_star_field

if TYPE_CHECKING:
    from boogiestats.boogie_api.models import Player, Song

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
        itg_score: int,
        comment: str,
        rate: int,
        used_cmod: Optional[bool] = None,
        judgments: Optional = None,
    ):
        used_cmod = self._handle_used_cmod(used_cmod, comment)
        new_is_itg_top, previous_itg_top = self._handle_is_itg_top(song, player, itg_score)

        score_object = self.model(
            song=song,
            player=player,
            itg_score=itg_score,
            comment=comment,
            is_itg_top=new_is_itg_top,
            rate=rate,
            used_cmod=used_cmod,
        )

        self._handle_judgments(score_object, judgments)
        new_is_ex_top = self._handle_is_ex_top(song, player, score_object.ex_score)
        score_object.is_ex_top = new_is_ex_top

        score_object.save()

        self._update_song(score_object, song)
        self._update_player(score_object, player, previous_itg_top, new_is_itg_top, new_is_ex_top)
        song.update_search_cache()  # TODO: this *really* needs to be done async

        return score_object

    def _handle_used_cmod(self, used_cmod, comment):
        if used_cmod is None:  # fallback to comment parsing
            # Just a trivial check because I don't really care about false-positives much,
            # update your client if you wish to have accurate stats ¯\_(ツ)_/¯
            used_cmod = "C" in comment

        return used_cmod

    def _handle_is_itg_top(self, song, player, score):
        new_is_itg_top = False

        try:
            previous_top = song.scores.get(player=player, is_itg_top=True)
        except ObjectDoesNotExist:
            previous_top = None
            new_is_itg_top = True

        if previous_top and previous_top.itg_score < score:
            new_is_itg_top = True
            previous_top.is_itg_top = False
            previous_top.save()

        return new_is_itg_top, previous_top

    def _handle_is_ex_top(self, song, player, ex_score):
        new_is_ex_top = False

        try:
            previous_top = song.scores.get(player=player, is_ex_top=True)
        except ObjectDoesNotExist:
            previous_top = None
            new_is_ex_top = True

        if previous_top and previous_top.ex_score < ex_score:
            new_is_ex_top = True
            previous_top.is_ex_top = False
            previous_top.save()

        return new_is_ex_top

    def _handle_judgments(self, score_object, judgments):
        if judgments is not None:
            score_object.has_judgments = True
            for src, dst in JUDGMENTS_MAP.items():
                setattr(score_object, dst, judgments.get(src, 0))

            score_object.ex_score = score_object.calculate_ex()

    def _update_song(self, score_object, song):
        if not song.itg_highscore or score_object.itg_score > song.itg_highscore.itg_score:
            song.itg_highscore = score_object

        if not song.ex_highscore or score_object.ex_score > song.ex_highscore.ex_score:
            song.ex_highscore = score_object

        song.update_number_of_players_and_scores()
        song.save()

    def _update_player(self, score_object, player, previous_itg_top, itg_improved, ex_improved):
        player.latest_score = score_object
        player.num_scores += 1

        if itg_improved and (increase_star_field := score_to_star_field(score_object)):
            old_value = getattr(player, increase_star_field)
            setattr(player, increase_star_field, old_value + 1)

            if (previous_itg_top is not None) and (decrease_star_field := score_to_star_field(previous_itg_top)):
                old_value = getattr(player, decrease_star_field)
                setattr(player, decrease_star_field, old_value - 1)

        if ex_improved and score_object.ex_score == 10_000:
            player.five_stars += 1

        if previous_itg_top is None:
            player.num_songs += 1

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
