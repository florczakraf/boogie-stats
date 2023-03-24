import datetime
import itertools

import sentry_sdk
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
from redis import ResponseError
from redis.commands.search.query import Query

from boogiestats.boogie_api.models import Score, Player, Song
from boogiestats.boogie_api.utils import get_redis
from boogiestats.boogie_ui.forms import EditPlayerForm
from boogiestats.boogiestats.exceptions import Managed404Error

ENTRIES_PER_PAGE = 30
CALENDAR_VALUES = (1, 10, 15, 20, 25, 30, 35, 40, 50, 60)
EXTRA_CALENDAR_VALUES = (100,)


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
    class_suffix = 0
    for mapping in CALENDAR_VALUES + EXTRA_CALENDAR_VALUES:
        if plays >= mapping:
            class_suffix = mapping

    return f"min-plays-{class_suffix}"


class PlayerScoresByDayView(generic.ListView):
    template_name = "boogie_ui/scores_by_day.html"
    context_object_name = "scores"
    paginate_by = ENTRIES_PER_PAGE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        player_id = self.kwargs["player_id"]
        player = Player.get_or_404(id=player_id)
        day = datetime.date.fromisoformat(self.kwargs["day"])
        scores = player.scores.filter(submission_day=day)
        context["day"] = day
        context["player"] = player
        context["num_scores"] = scores.count()
        context["num_charts_played"] = scores.values("song").distinct().count()
        context["one_star"] = scores.filter(is_top=True, score__gte=9600, score__lt=9800).count()
        context["two_stars"] = scores.filter(is_top=True, score__gte=9800, score__lt=9900).count()
        context["three_stars"] = scores.filter(is_top=True, score__gte=9900, score__lt=10000).count()
        context["four_stars"] = scores.filter(is_top=True, score=10000).count()

        return context

    def get_queryset(self):
        player_id = self.kwargs["player_id"]
        player = Player.get_or_404(id=player_id)
        day = datetime.date.fromisoformat(self.kwargs["day"])
        scores = player.scores.filter(submission_day=day)

        return scores.order_by("-submission_date").prefetch_related("song")


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
        context["calendar_legend"] = tuple(
            [("0", "min-plays-0")] + [(f"{number}+", f"min-plays-{number}") for number in CALENDAR_VALUES]
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


class PlayerMostPlayedView(PlayerView):
    def get_queryset(self):
        return None

    def get_context_data(self, **kwargs):
        self.paginate_by = None  # automatic pagination fails, we do it manually in this case because of aggregation
        context = super().get_context_data(**kwargs)

        player = context["player"]
        songs_by_plays = player.scores.values("song").annotate(num_scores=Count("song")).order_by("-num_scores")
        paginator, page, songs_by_plays_page, is_paginated = self.paginate_queryset(songs_by_plays, ENTRIES_PER_PAGE)

        songs = [song["song"] for song in songs_by_plays_page]
        songs_plays = {song["song"]: song["num_scores"] for song in songs_by_plays_page}
        scores = player.scores.filter(is_top=True, song__hash__in=songs).prefetch_related("song")

        scores = sorted(scores, key=lambda x: songs.index(x.song.hash))
        for score in scores:
            setattr(score, "num_scores", songs_plays[score.song.hash])

        context.update(
            {
                "paginator": paginator,
                "page_obj": page,
                "is_paginated": is_paginated,
                "scores": scores,
            }
        )
        return context


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

    def sort_key(self, x):
        return x[0].score

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
            key=self.sort_key,
            reverse=True,
        )
        paginator, page, score_page, is_paginated = self.paginate_queryset(scores, ENTRIES_PER_PAGE)

        context["p1_num_scores"] = p1.scores.count()
        context["p1_num_charts_played"] = p1.scores.filter(is_top=True).count()
        context["p1_wins"] = sum((1 for x in scores if x[0].score > x[1].score))
        context["p1_one_star"] = p1.scores.filter(is_top=True, score__gte=9600, score__lt=9800).count()
        context["p1_two_stars"] = p1.scores.filter(is_top=True, score__gte=9800, score__lt=9900).count()
        context["p1_three_stars"] = p1.scores.filter(is_top=True, score__gte=9900, score__lt=10000).count()
        context["p1_four_stars"] = p1.scores.filter(is_top=True, score=10000).count()

        context["p2_num_scores"] = p2.scores.count()
        context["p2_num_charts_played"] = p2.scores.filter(is_top=True).count()
        context["p2_wins"] = sum((1 for x in scores if x[0].score < x[1].score))
        context["p2_one_star"] = p2.scores.filter(is_top=True, score__gte=9600, score__lt=9800).count()
        context["p2_two_stars"] = p2.scores.filter(is_top=True, score__gte=9800, score__lt=9900).count()
        context["p2_three_stars"] = p2.scores.filter(is_top=True, score__gte=9900, score__lt=10000).count()
        context["p2_four_stars"] = p2.scores.filter(is_top=True, score=10000).count()

        context["ties"] = len(scores) - context["p1_wins"] - context["p2_wins"]
        context["common_charts"] = len(scores)

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


class VersusByDifferenceView(VersusView):
    def sort_key(self, x):
        return x[0].score - x[1].score


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

        if player_id := self.kwargs.get("player_id"):
            context["player"] = Player.get_or_404(id=player_id)

        return context

    def get_queryset(self):
        song_hash = self.kwargs["song_hash"]
        return (
            Song.get_or_404(hash=song_hash)
            .scores.order_by("-score", "submission_date")
            .select_related("song", "player")
        )


class ScoreView(generic.DetailView):
    template_name = "boogie_ui/score.html"
    model = Score


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


def user_manual(request):
    port = request.get_port()
    boogiestats_allow_host = request.get_host().removesuffix(f":{port}")  # exclude any ports if present

    # TODO: this uses a WA for reverse proxies that just replaces http with https
    boogiestats_url_prefix = (
        request.build_absolute_uri().replace("http:", "https:").removesuffix(request.get_full_path()) + "/"
    )

    return render(
        request,
        template_name="boogie_ui/manual.html",
        context={"boogiestats_allow_host": boogiestats_allow_host, "boogiestats_url_prefix": boogiestats_url_prefix},
    )


class SearchView(generic.ListView):
    template_name = "boogie_ui/search.html"

    def _process_query(self, user_query):
        query_elements = user_query.split()

        for i, e in enumerate(query_elements):
            if e.startswith("-"):
                continue

            if e.startswith("@"):
                continue

            if e.startswith('"') or e.startswith("'"):
                continue

            query_elements[i] = f"%{e}%"

        return " ".join(query_elements)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        r = get_redis()
        if not r:
            return context

        index = r.ft("idx:song")
        user_query = self.request.GET.get("q", "")
        processed_query = self._process_query(user_query)

        q = (
            Query(processed_query)
            .paging((int(self.request.GET.get("page", 1)) - 1) * ENTRIES_PER_PAGE, ENTRIES_PER_PAGE)
            .sort_by("num_plays", asc=False)
        )
        n_results = 0
        results = []
        try:
            redis_search_results = index.search(q)
            n_results = redis_search_results.total
            results = redis_search_results.docs
        except ResponseError as e:
            sentry_sdk.capture_exception(e)
            if "no such index" in str(e):
                message = "BoogieStats instance seems to be misconfigured. Consider letting your admin know about this."
            else:
                message = "Query syntax error. Consider removing/escaping special characters."
            messages.error(
                self.request,
                message,
                extra_tags="alert-danger",
            )

        hashes = []
        for result in results:
            song_hash = result.id.removeprefix("song:")
            hashes.append(song_hash)

        songs = (
            Song.objects.filter(hash__in=hashes)
            .annotate(num_scores=Count("scores"), num_players=Count("scores__player", distinct=True))
            .prefetch_related("highscore", "highscore__player")
            .order_by("-num_scores", "-highscore__score")
        )

        paginator, page, _, is_paginated = self.paginate_queryset(range(n_results), ENTRIES_PER_PAGE)

        context.update(
            {
                "paginator": paginator,
                "page_obj": page,
                "is_paginated": is_paginated,
                "songs": songs,
                "user_query": user_query,
            }
        )

        return context

    def get_queryset(self):
        return None
