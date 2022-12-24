import datetime
import itertools

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.db.models import Count
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views import generic

from boogiestats.boogie_api.models import Score, Player, Song
from boogiestats.boogie_ui.forms import EditPlayerForm
from boogiestats.boogiestats.exceptions import Managed404Error

ENTRIES_PER_PAGE = 30


class IndexView(generic.ListView):
    template_name = "boogie_ui/index.html"
    context_object_name = "latest_scores"

    def get_queryset(self):
        return Score.objects.order_by("-submission_date").select_related("song", "player")[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["n_songs"] = Song.objects.count()
        context["n_scores"] = Score.objects.count()
        context["n_players"] = Player.objects.count()
        context["recent_activity"] = Player.objects.order_by("-latest_score__submission_date").select_related(
            "latest_score", "latest_score__song"
        )[:5]

        return context


class ScoreListView(generic.ListView):
    template_name = "boogie_ui/scores.html"
    context_object_name = "scores"
    paginate_by = ENTRIES_PER_PAGE

    def get_queryset(self):
        return Score.objects.order_by("-submission_date").select_related("song", "player")


class HighscoreListView(ScoreListView):
    def get_queryset(self):
        return Score.objects.order_by("-score", "submission_date").select_related("song", "player")


class PlayersListView(generic.ListView):
    template_name = "boogie_ui/players.html"
    context_object_name = "players"
    paginate_by = ENTRIES_PER_PAGE

    def get_queryset(self):
        return Player.objects.all().annotate(num_scores=Count("scores")).order_by("id")


class PlayersByNameListView(PlayersListView):
    def get_queryset(self):
        return Player.objects.all().annotate(num_scores=Count("scores")).order_by(Lower("name"))


class PlayersByMachineTagListView(PlayersListView):
    def get_queryset(self):
        return Player.objects.all().annotate(num_scores=Count("scores")).order_by(Lower("machine_tag"))


class PlayersByScoresListView(PlayersListView):
    def get_queryset(self):
        return Player.objects.all().annotate(num_scores=Count("scores")).order_by("-num_scores")


def plays_to_class(plays):
    mappings = (1, 10, 15, 20)
    class_suffix = 0
    for mapping in mappings:
        if plays >= mapping:
            class_suffix = mapping

    return f"min-plays-{class_suffix}"


class PlayerView(generic.ListView):
    template_name = "boogie_ui/player.html"
    context_object_name = "scores"
    paginate_by = ENTRIES_PER_PAGE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        player_id = self.kwargs["player_id"]
        player = Player.get_or_404(id=player_id)
        context["player"] = player
        context["rivals"] = player.rivals.all()
        scores = player.scores
        context["num_scores"] = scores.count()
        context["num_charts_played"] = scores.filter(is_top=True).count()
        context["one_star"] = scores.filter(is_top=True, score__gte=9600, score__lt=9800).count()
        context["two_stars"] = scores.filter(is_top=True, score__gte=9800, score__lt=9900).count()
        context["three_stars"] = scores.filter(is_top=True, score__gte=9900, score__lt=10000).count()
        context["four_stars"] = scores.filter(is_top=True, score=10000).count()

        today = datetime.date.today()
        a_year_ago = today.replace(year=today.year - 1)

        context["skip_days_range"] = range(a_year_ago.timetuple().tm_wday)

        context["start_date"] = a_year_ago
        played_days = (
            player.scores.values("submission_day")
            .filter(submission_day__gte=a_year_ago)
            .annotate(plays=Count("submission_day"))
            .all()
        )

        calendar_days = list(
            {"class": "min-plays-0", "plays": 0, "day": a_year_ago + datetime.timedelta(days=i)}
            for i in range((today - a_year_ago).days + 1)
        )
        for day in played_days:
            day_index = (day["submission_day"] - a_year_ago).days
            plays = day["plays"]
            calendar_days[day_index]["plays"] = plays
            calendar_days[day_index]["class"] = plays_to_class(plays)

        context["calendar_days"] = calendar_days

        # sometimes it looks better to repeat the month at both ends
        num_months = 13 if a_year_ago.day > 4 else 12
        months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        months_iterator = itertools.cycle(months)
        for _ in range(today.month - 1):
            next(months_iterator)
        context["months"] = list(next(months_iterator) for _ in range(num_months))

        context["days"] = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        context["calendar_legend"] = (
            ("0", "min-plays-0"),
            ("1+", "min-plays-1"),
            ("10+", "min-plays-10"),
            ("15+", "min-plays-15"),
            ("20+", "min-plays-20"),
        )

        return context

    def get_queryset(self):
        player_id = self.kwargs["player_id"]
        player = Player.get_or_404(id=player_id)

        return player.scores.order_by("-submission_date").prefetch_related("song")


class PlayerHighscoresView(PlayerView):
    def get_queryset(self):
        player_id = self.kwargs["player_id"]
        player = Player.get_or_404(id=player_id)

        return player.scores.filter(is_top=True).order_by("-score").prefetch_related("song")


class PlayerStatsView(generic.base.TemplateView):
    template_name = "boogie_ui/player_stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        player_id = self.kwargs["player_id"]
        player = Player.get_or_404(id=player_id)
        context["player"] = player
        scores = player.scores

        context["num_scores"] = scores.count()
        context["num_charts_played"] = scores.filter(is_top=True).count()
        context["one_star"] = scores.filter(is_top=True, score__gte=9600, score__lt=9800).count()
        context["two_stars"] = scores.filter(is_top=True, score__gte=9800, score__lt=9900).count()
        context["three_stars"] = scores.filter(is_top=True, score__gte=9900, score__lt=10000).count()
        context["four_stars"] = scores.filter(is_top=True, score=10000).count()

        return context


class VersusView(generic.ListView):
    template_name = "boogie_ui/versus.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        p1, p2 = self.get_players()
        p1_scores_qs = p1.scores.filter(is_top=True).order_by("-score").all().select_related("song")
        p2_scores_qs = p2.scores.filter(is_top=True, song__hash__in=[score.song_id for score in p1_scores_qs])
        p2_scores_dict = {score.song_id: score for score in p2_scores_qs}
        scores = sorted(
            [
                (p1_score, p2_scores_dict[p1_score.song_id])
                for p1_score in p1_scores_qs
                if p1_score.song_id in p2_scores_dict
            ],
            key=lambda x: x[0].score,
            reverse=True,
        )
        paginator, page, score_page, is_paginated = self.paginate_queryset(scores, ENTRIES_PER_PAGE)

        context.update(
            {
                "paginator": paginator,
                "page_obj": page,
                "is_paginated": is_paginated,
                "scores": score_page,
                "p1": p1,
                "p2": p2,
            }
        )

        return context

    def get_players(self):
        p1 = Player.get_or_404(id=self.kwargs["p1"])
        p2 = Player.get_or_404(id=self.kwargs["p2"])
        return p1, p2

    def get_queryset(self):
        return None


class SongView(generic.ListView):
    template_name = "boogie_ui/song.html"
    context_object_name = "scores"
    paginate_by = ENTRIES_PER_PAGE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        song_hash = self.kwargs["song_hash"]
        song = Song.get_or_404(hash=song_hash)
        context["song"] = song
        context["num_highscores"] = song.scores.filter(is_top=True).count()
        if hasattr(self.request.user, "player"):
            context["my_scores"] = song.scores.filter(player=self.request.user.player).count()

        if "player_id" in self.kwargs:
            context["player"] = Player.get_or_404(id=self.kwargs["player_id"])

        return context

    def get_queryset(self):
        song_hash = self.kwargs["song_hash"]
        return (
            Song.get_or_404(hash=song_hash)
            .scores.order_by("-score", "submission_date")
            .select_related("song", "player")
        )


class SongHighscoresView(SongView):
    def get_queryset(self):
        song_hash = self.kwargs["song_hash"]
        return (
            Song.get_or_404(hash=song_hash)
            .scores.filter(is_top=True)
            .order_by("-score", "submission_date")
            .select_related("song", "player")
        )


class SongByPlayerView(SongView):
    def get_queryset(self):
        player = Player.get_or_404(id=self.kwargs["player_id"])
        song = Song.get_or_404(hash=self.kwargs["song_hash"])
        return song.scores.filter(player=player).order_by("-score", "submission_date").select_related("song", "player")


class SongsListView(generic.ListView):
    template_name = "boogie_ui/songs.html"
    context_object_name = "songs"
    paginate_by = ENTRIES_PER_PAGE

    def get_queryset(self):
        return (
            Song.objects.all()
            .prefetch_related("scores__player")
            .annotate(num_scores=Count("scores"), num_players=Count("scores__player", distinct=True))
            .order_by("-num_scores")
            .prefetch_related(
                "highscore",
                "highscore__player",
            )
        )


class SongsByPlayersListView(SongsListView):
    def get_queryset(self):
        return (
            Song.objects.all()
            .prefetch_related("scores__player")
            .annotate(num_scores=Count("scores"), num_players=Count("scores__player", distinct=True))
            .order_by("-num_players")
            .prefetch_related("highscore", "highscore__player")
        )


class EditPlayerView(LoginRequiredMixin, generic.UpdateView):
    login_url = "/login/"
    template_name = "boogie_ui/player_update.html"
    form_class = EditPlayerForm

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


class Response404(TemplateResponse):
    status_code = 404


class Handler404(generic.base.TemplateView):
    response_class = Response404
    template_name = "boogie_ui/404.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fallback_exception = "Page not found."

        context["exception"] = context.get("exception")
        if not isinstance(context["exception"], Managed404Error):
            context["exception"] = fallback_exception

        return context
