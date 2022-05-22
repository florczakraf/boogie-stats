from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.db.models import Count
from django.urls import reverse
from django.views import generic

from boogiestats.boogie_api.models import Score, Player, Song


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

    return render(request, template_name="boogie_ui/login.html", context={"next": request.GET.get("next")})
