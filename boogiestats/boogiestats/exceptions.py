from django.http import Http404


class Managed404Error(Http404):
    pass
