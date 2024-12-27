from django.http import JsonResponse
from django.views import View

from boogiestats.boogie_api.models import Player


class LiveOnTwitch(View):
    def get(self, request, player_id, *args, **kwargs):
        player = Player.get_or_404(id=player_id)
        return JsonResponse({"is_live": player.is_live()})
