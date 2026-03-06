from django.http import Http404, JsonResponse
from django.urls import path
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt

from . import v1, views
from .views import GROOVESTATS_RESPONSES

cached_new_session = cache_page(60 * 60)(views.new_session)


@csrf_exempt
def action_dispatcher(request):
    """
    GS has introduced another way of exposing APIs in 2026. Instead of separate PHP
    scripts, there's a single dispatcher mounted in some directory. It slightly complicates
    things on our end because we didn't prefix GS API, so we need to serve both GS API
    *and* our landing page from the same path to maintain backward compatibility for users
    that already have BS configured.

    https://github.com/Simply-Love/Simply-Love-SM5/commit/0c1d48996b63a81aad1e870af942d7066f018360
    """
    action = request.GET.get("action", "")

    if not action:
        raise Http404()

    action_handlers = {
        "newSession": cached_new_session,
        "playerScores": views.player_scores,
        "playerLeaderboards": views.player_leaderboards,
        "scoreSubmit": views.score_submit,
    }

    if action in action_handlers:
        return action_handlers[action](request)

    return JsonResponse(
        GROOVESTATS_RESPONSES["INVALID_ACTION"],
        status=400,
    )


GS = [
    path("new-session.php", cached_new_session),
    path("player-scores.php", views.player_scores),
    path("player-leaderboards.php", views.player_leaderboards),
    path("score-submit.php", views.score_submit),
]

BS_V1 = [
    path("api/v1/live-on-twitch/<int:player_id>/", v1.LiveOnTwitch.as_view()),
]

urlpatterns = GS + BS_V1
