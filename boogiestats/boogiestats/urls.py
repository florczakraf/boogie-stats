from django.contrib import admin
from django.urls import include, path

from boogiestats.boogie_ui.views import Handler404

urlpatterns = [
    path("", include("boogiestats.boogie_ui.urls")),
    path("", include("boogiestats.boogie_api.urls")),
    path("admin/", admin.site.urls),
    path("", include("django_prometheus.urls")),
]

handler404 = Handler404.as_view()
