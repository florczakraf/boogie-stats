#!/usr/bin/env python3

import django
from redis import ResponseError
from redis.commands.search.field import NumericField, TagField, TextField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType


def setup_index(r):
    schema = (
        TextField("title", sortable=True),
        TextField("titletranslit", sortable=True),
        TextField("subtitle", sortable=True),
        TextField("subtitletranslit", sortable=True),
        TextField("artist", sortable=True),
        TextField("artisttranslit", sortable=True),
        TextField("pack_name", sortable=True),
        TagField("diff", sortable=True),
        TagField("steps_type", sortable=True),
        NumericField("diff_number", sortable=True),
        NumericField("num_plays", sortable=True),
    )
    try:
        r.ft("idx:song").create_index(schema, definition=IndexDefinition(prefix=["song:"], index_type=IndexType.HASH))
    except ResponseError as e:
        if "Index already exists" not in str(e):
            raise


def populate_cache(r):
    from boogiestats.boogie_api.models import Song

    songs = Song.objects.all()

    n = 0
    for song in songs:
        cache_updated = song.update_search_cache(redis_connection=r)
        if cache_updated:
            n += 1

    print(f"Added {n} out of {songs.count()} songs to the redis index")


def main():
    django.setup()

    from boogiestats.boogie_api.utils import get_redis

    r = get_redis()
    if not r:
        print("Redis not configured, search functionality will not be enabled.")
        return

    setup_index(r)
    populate_cache(r)


if __name__ == "__main__":
    main()
