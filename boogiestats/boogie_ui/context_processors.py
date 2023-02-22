from django.conf import settings

from boogiestats.boogie_api.utils import search_enabled


def logo(request):
    return {"BS_LOGO_PATH": settings.BS_LOGO_PATH, "BS_LOGO_CREDITS": settings.BS_LOGO_CREDITS}


def search(request):
    return {"BS_SEARCH_ENABLED": search_enabled()}
