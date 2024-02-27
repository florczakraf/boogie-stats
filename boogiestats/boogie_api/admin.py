from django.contrib import admin
from boogiestats.boogie_api.models import Score, Player, Song


class PlayerAdmin(admin.ModelAdmin):
    # we need to exclude foreign models, otherwise the admin won't load in sensible time
    readonly_fields = (
        "user",
        "api_key",
        "latest_score",
    )


class ScoreAdmin(admin.ModelAdmin):
    # we need to exclude foreign models, otherwise the admin won't load in sensible time
    readonly_fields = (
        "song",
        "player",
    )


class SongAdmin(admin.ModelAdmin):
    # we need to exclude foreign models, otherwise the admin won't load in sensible time
    fields = (
        "hash",
        "gs_ranked",
        "itg_highscore",
        "ex_highscore",
        "number_of_scores",
        "number_of_players",
    )
    readonly_fields = (
        "hash",
        "itg_highscore",
        "ex_highscore",
        "number_of_scores",
        "number_of_players",
    )


admin.site.register(Player, PlayerAdmin)
admin.site.register(Score, ScoreAdmin)
admin.site.register(Song, SongAdmin)
