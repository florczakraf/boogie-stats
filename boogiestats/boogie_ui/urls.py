from django.urls import path

from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("players/", views.PlayersListView.as_view(), name="players"),
    path("players/<int:player_id>/", views.PlayerView.as_view(), name="player"),
    path("players/<int:player_id>/highscores", views.PlayerHighscoresView.as_view(), name="player_highscores"),
    path("players/<int:player_id>/stats", views.PlayerStatsView.as_view(), name="player_stats"),
    path("players/<int:p1>/vs/<int:p2>/", views.VersusView.as_view(), name="versus"),
    path("songs/", views.SongsListView.as_view(), name="songs"),
    path("songs/<str:song_hash>/", views.SongView.as_view(), name="song"),
    path("songs/<str:song_hash>/highscores", views.SongHighscoresView.as_view(), name="song_highscores"),
    path("edit/", views.EditPlayerView.as_view(), name="edit"),
    path("login/", views.login_user, name="login"),
    path("logout/", views.logout_user, name="logout"),
]
