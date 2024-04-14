from typing import Optional

import redis
import sentry_sdk
from django.conf import settings
from django.http import HttpRequest
from ipware import get_client_ip

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from boogiestats.boogie_api.models import Player, Score


def search_enabled() -> bool:
    return settings.BS_REDIS_HOST and settings.BS_REDIS_PORT


def get_redis() -> Optional[redis.Redis]:
    if search_enabled():
        return redis.Redis(host=settings.BS_REDIS_HOST, port=settings.BS_REDIS_PORT)


def set_sentry_user(request: HttpRequest, player_instance: Optional["Player"] = None):
    if not player_instance and request.user:
        player_instance = getattr(request.user, "player", None)  # AnonymousUsers don't have player field

    if player_instance is not None:
        sentry_sdk.set_user(
            {"id": player_instance.id, "username": player_instance.name, "ip_address": get_client_ip(request)[0]}
        )


def score_to_star_field(score: "Score"):
    value = score.itg_score
    if 9600 <= value < 9800:
        return "one_star"
    elif 9800 <= value < 9900:
        return "two_stars"
    elif 9900 <= value < 10_000:
        return "three_stars"
    elif value == 10_000:
        return "four_stars"

    return None
