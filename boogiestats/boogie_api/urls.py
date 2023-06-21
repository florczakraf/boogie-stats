from django.urls import path
from django.views.decorators.cache import cache_page

from . import views

urlpatterns = [
    path("new-session.php", cache_page(60 * 60)(views.new_session)),
    path("player-scores.php", views.player_scores),
    path("player-leaderboards.php", views.player_leaderboards),
    path("score-submit.php", views.score_submit),
]
