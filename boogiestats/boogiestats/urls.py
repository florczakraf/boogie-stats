from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt

from boogiestats.boogie_api.urls import action_dispatcher
from boogiestats.boogie_ui.views import Handler404, IndexView


@csrf_exempt
def root_dispatcher(request):
    action = request.GET.get("action", "")

    if action:
        return action_dispatcher(request)

    return IndexView.as_view()(request)


urlpatterns = [
    path("", root_dispatcher),
    path("", include("boogiestats.boogie_ui.urls")),
    path("", include("boogiestats.boogie_api.urls")),
    path("admin/", admin.site.urls),
    path("", include("django_prometheus.urls")),
]

handler404 = Handler404.as_view()
