from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("players/", views.PlayersListView.as_view(), name="players"),
    path("edit/", views.EditPlayerView.as_view(), name="edit"),
    path("login/", views.login_user, name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
