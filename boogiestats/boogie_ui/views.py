from django.db.models import Count
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
        # return Player.objects.order_by("-scores__count")
