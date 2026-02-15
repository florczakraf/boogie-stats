import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import redis
import sentry_sdk
from django.conf import settings
from django.http import HttpRequest
from ipware import get_client_ip

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


def get_chart_info(hash_v3: str) -> dict | None:
    """Chart info based on an external (optional) chart database"""
    if settings.BS_CHART_DB_PATH is None:
        return None

    base_path = (Path(settings.BS_CHART_DB_PATH) / "charts").resolve()
    path = (base_path / hash_v3[:2] / f"{hash_v3[2:]}.json").resolve()
    if path.is_relative_to(base_path) and path.exists():
        return json.loads(path.read_text())
    return None


def get_pack_info(pack_name: str) -> dict | None:
    if settings.BS_CHART_DB_PATH is None:
        return None

    base_path = (Path(settings.BS_CHART_DB_PATH) / "packs").resolve()
    path = (base_path / f"{pack_name}.json").resolve()
    if path.is_relative_to(base_path) and path.exists():
        return json.loads(path.read_text())
    return None


def get_display_name(chart_info: dict, *, with_steps_type: bool = True) -> str:
    artist = chart_info["artisttranslit"] or chart_info["artist"]
    title = chart_info["titletranslit"] or chart_info["title"]

    subtitle = chart_info["subtitletranslit"] or chart_info["subtitle"]
    if subtitle:
        if not (subtitle.startswith("(") and subtitle.endswith(")")):  # fix inconsistent braces
            subtitle = f"({subtitle})"
        subtitle = f" {subtitle}"

    base_display_name = f"{artist} - {title}{subtitle}"
    final_name = base_display_name

    if with_steps_type:
        steps_type = chart_info["steps_type"]
        # never display dance-single because it's most common chart type
        if steps_type != "dance-single":
            final_name += f" ({steps_type})"

    return final_name
