from django.urls import path

from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("players/", views.PlayersListView.as_view(), name="players"),
    path("players_by_name/", views.PlayersByNameListView.as_view(), name="players_by_name"),
    path("players_by_machine_tag/", views.PlayersByMachineTagListView.as_view(), name="players_by_machine_tag"),
    path("players_by_scores/", views.PlayersByScoresListView.as_view(), name="players_by_scores"),
    path("players_by_quads/", views.PlayersByQuadsListView.as_view(), name="players_by_quads"),
    path("players_by_quints/", views.PlayersByQuintsListView.as_view(), name="players_by_quints"),
    path("players_by_songs/", views.PlayersBySongsListView.as_view(), name="players_by_songs"),
    path("players/<int:player_id>/", views.PlayerView.as_view(), name="player"),
    path("players/<int:player_id>/most_played", views.PlayerMostPlayedView.as_view(), name="player_most_played"),
    path("players/<int:player_id>/highscores", views.PlayerHighscoresView.as_view(), name="player_highscores"),
    path("players/<int:player_id>/stats", views.PlayerStatsView.as_view(), name="player_stats"),
    path("players/<int:player_id>/wrapped/<int:year>", views.PlayerWrappedView.as_view(), name="wrapped"),
    path("players/<int:player_id>/add_rival", views.add_rival, name="add_rival"),
    path("players/<int:player_id>/remove_rival", views.remove_rival, name="remove_rival"),
    path("players/<int:player_id>/day/today", views.PlayerScoresTodayView.as_view(), name="player_scores_today"),
    path("players/<int:player_id>/day/<str:day>", views.PlayerScoresByDayView.as_view(), name="player_scores_by_day"),
    path("players/<int:p1>/vs/<int:p2>/", views.VersusView.as_view(), name="versus"),
    path(
        "players/<int:p1>/vs_by_difference/<int:p2>/",
        views.VersusByDifferenceView.as_view(),
        name="versus_by_difference",
    ),
    path("songs/", views.SongsListView.as_view(), name="songs"),
    path("songs_by_players/", views.SongsByPlayersListView.as_view(), name="songs_by_players"),
    path("song_by_player/<str:song_hash>/<int:player_id>", views.SongByPlayerView.as_view(), name="song_by_player"),
    path("song_by_rivals/<str:song_hash>/<int:player_id>", views.SongByRivalsView.as_view(), name="song_by_rivals"),
    path("songs/<str:song_hash>/", views.SongView.as_view(), name="song"),
    path("song_by_date/<str:song_hash>/", views.SongByDateView.as_view(), name="song_by_date"),
    path("songs/<str:song_hash>/highscores", views.SongHighscoresView.as_view(), name="song_highscores"),
    path("scores/", views.ScoreListView.as_view(), name="scores"),
    path("scores/<int:pk>/", views.ScoreView.as_view(), name="score"),
    path("edit/", views.EditPlayerView.as_view(), name="edit"),
    path("login/", views.login_user, name="login"),
    path("logout/", views.logout_user, name="logout"),
    path("manual/", views.user_manual, name="manual"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("my-profile/", views.MyProfileView.as_view(), name="my-profile"),

    path("stats/", views.stats, name="stats")
]
