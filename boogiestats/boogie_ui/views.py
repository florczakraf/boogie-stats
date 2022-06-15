from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.db.models import Count
from django.urls import reverse
from django.views import generic

from boogiestats.boogie_api.models import Score, Player, Song

ENTRIES_PER_PAGE = 30


class IndexView(generic.ListView):
    template_name = "boogie_ui/index.html"
    context_object_name = "latest_scores"

    def get_queryset(self):
        return Score.objects.order_by("-submission_date")[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["n_songs"] = Song.objects.count()
        context["n_scores"] = Score.objects.count()
        context["n_players"] = Player.objects.count()
        return context


class PlayersListView(generic.ListView):
    template_name = "boogie_ui/players.html"
    context_object_name = "players"

    def get_queryset(self):
        return Player.objects.all().annotate(num_scores=Count("scores")).order_by("machine_tag")


class PlayerView(generic.ListView):
    template_name = "boogie_ui/player.html"
    context_object_name = "scores"
    paginate_by = ENTRIES_PER_PAGE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        player_id = self.kwargs["player_id"]
        context["player"] = Player.objects.get(id=player_id)

        return context

    def get_queryset(self):
        player_id = self.kwargs["player_id"]
        return Player.objects.get(id=player_id).scores.filter(is_top=True).order_by("-submission_date")


class SongView(generic.ListView):
    template_name = "boogie_ui/song.html"
    context_object_name = "scores"
    paginate_by = ENTRIES_PER_PAGE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        song_hash = self.kwargs["song_hash"]
        context["song"] = Song.objects.get(hash=song_hash)

        return context

    def get_queryset(self):
        song_hash = self.kwargs["song_hash"]
        return Song.objects.get(hash=song_hash).scores.order_by("-score", "submission_date")


class SongsListView(generic.ListView):
    template_name = "boogie_ui/songs.html"
    context_object_name = "songs"
    paginate_by = ENTRIES_PER_PAGE

    def get_queryset(self):
        return Song.objects.all().annotate(num_scores=Count("scores")).order_by("-num_scores")


class EditPlayerView(LoginRequiredMixin, generic.UpdateView):
    login_url = "/login/"
    template_name = "boogie_ui/player_update.html"
    model = Player
    fields = ["machine_tag", "rivals", "name"]  # TODO api key?

    def get_object(self, **kwargs):
        return self.request.user.player

    def get_success_url(self):
        return reverse("edit")


def login_user(request):
    if request.POST:
        gs_api_key = request.POST["gs_api_key"]

        user = authenticate(request, gs_api_key=gs_api_key)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(request.POST.get("next") or "/")
        else:
            messages.error(request, "Invalid GS API Key, please try again", extra_tags="alert-danger")

    next = request.GET.get("next") or request.POST.get("next")
    return render(request, template_name="boogie_ui/login.html", context={"next": next})


def logout_user(request):
    logout(request)
    messages.success(request, "Logged out successfully.", extra_tags="alert-success")
    return redirect(reverse("index"))
