from django.conf import settings


def logo(request):
    return {"BS_LOGO_PATH": settings.BS_LOGO_PATH, "BS_LOGO_CREDITS": settings.BS_LOGO_CREDITS}
