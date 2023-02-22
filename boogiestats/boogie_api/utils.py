from typing import Optional

import redis
from django.conf import settings


def search_enabled() -> bool:
    return settings.BS_REDIS_HOST and settings.BS_REDIS_PORT


def get_redis() -> Optional[redis.Redis]:
    if search_enabled():
        return redis.Redis(host=settings.BS_REDIS_HOST, port=settings.BS_REDIS_PORT)
