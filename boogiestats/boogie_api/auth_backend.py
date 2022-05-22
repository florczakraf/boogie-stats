from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User

from boogiestats.boogie_api.models import Player


class GSApiKeyBackend(BaseBackend):
    def authenticate(self, request, gs_api_key=None):
        if player := Player.get_by_gs_api_key(gs_api_key):
            return player.user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
