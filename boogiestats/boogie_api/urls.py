from django.urls import path
from django.views.decorators.cache import cache_page

from . import v1, views

GS = [
    path("new-session.php", cache_page(60 * 60)(views.new_session)),
    path("player-scores.php", views.player_scores),
    path("player-leaderboards.php", views.player_leaderboards),
    path("score-submit.php", views.score_submit),
]

BS_V1 = [
    path("api/v1/live-on-twitch/<int:player_id>/", v1.LiveOnTwitch.as_view()),
]

urlpatterns = GS + BS_V1
