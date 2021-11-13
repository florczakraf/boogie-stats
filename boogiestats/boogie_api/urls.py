from django.urls import path

from . import views

urlpatterns = [
    path("new-session.php", views.new_session),
    path("player-scores.php", views.player_scores),
    path("player-leaderboards.php", views.player_leaderboards),
    path("score-submit.php", views.score_submit),
]
