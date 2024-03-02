import datetime
import itertools
from http.client import UNAUTHORIZED, OK

import sentry_sdk
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.db.models import Count, Sum
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_POST
from redis import ResponseError
from redis.commands.search.query import Query

from boogiestats.boogie_api.models import Score, Player, Song
from boogiestats.boogie_api.utils import get_redis, set_sentry_user
from boogiestats.boogie_ui.forms import EditPlayerForm
from boogiestats.boogiestats.exceptions import Managed404Error

ENTRIES_PER_PAGE = 30
CALENDAR_VALUES = (1, 10, 15, 20, 25, 30, 35, 40, 50, 60)
EXTRA_CALENDAR_VALUES = (100,)


class LeaderboardSourceMixin:
    @property
    def lb_source(self):
        if self.request.COOKIES.get("bs_leaderboard") == "ex":
            return "ex"
        else:
            return "itg"

    @property
    def lb_attribute(self):
        return f"{self.lb_source}_score"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lb_display_name"] = self.lb_source.upper()
        context["lb_attribute"] = self.lb_attribute
        context["highscore_attribute"] = f"{self.lb_source}_highscore"

        return context


def set_stars(context, scores, prefix=""):
    context[f"{prefix}one_star"] = scores.filter(is_itg_top=True, itg_score__gte=9600, itg_score__lt=9800).count()
    context[f"{prefix}two_stars"] = scores.filter(is_itg_top=True, itg_score__gte=9800, itg_score__lt=9900).count()
    context[f"{prefix}three_stars"] = scores.filter(is_itg_top=True, itg_score__gte=9900, itg_score__lt=10000).count()
    context[f"{prefix}four_stars"] = scores.filter(is_itg_top=True, itg_score=10000).count()
    context[f"{prefix}five_stars"] = scores.filter(is_ex_top=True, ex_score=10000).count()


class IndexView(LeaderboardSourceMixin, generic.ListView):
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


class ScoreListView(LeaderboardSourceMixin, generic.ListView):
    template_name = "boogie_ui/scores.html"
    context_object_name = "scores"
    paginate_by = ENTRIES_PER_PAGE

    def get_queryset(self):
        return Score.objects.order_by("-submission_date").select_related("song", "player")


class HighscoreListView(ScoreListView):
    def get_queryset(self):
        return Score.objects.order_by(f"-{self.lb_attribute}", "submission_date").select_related("song", "player")


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


class PlayerScoresByDayView(LeaderboardSourceMixin, generic.ListView):
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
        set_stars(context, scores)
        context.update(
            fantastics_plus=0,
            fantastics=0,
            excellents=0,
            greats=0,
            decents=0,
            way_offs=0,
            misses=0,
            steps_hit=0,
        )

        if scores.count():
            sums = scores.aggregate(
                fantastics_plus=Sum("fantastics_plus"),
                fantastics=Sum("fantastics"),
                excellents=Sum("excellents"),
                greats=Sum("greats"),
                decents=Sum("decents"),
                way_offs=Sum("way_offs"),
                misses=Sum("misses"),
            )
            context["steps_hit"] = sum(sums.values()) - sums["misses"]
            context["total_steps"] = sum(sums.values())
            context.update(sums)

        return context

    def get_queryset(self):
        player_id = self.kwargs["player_id"]
        player = Player.get_or_404(id=player_id)
        day = datetime.date.fromisoformat(self.kwargs["day"])
        scores = player.scores.filter(submission_day=day)

        return scores.order_by("-submission_date").prefetch_related("song")


class PlayerView(LeaderboardSourceMixin, generic.ListView):
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
        context["num_charts_played"] = scores.filter(is_itg_top=True).count()
        set_stars(context, scores)

        today = datetime.date.today()
        a_year_ago = today - datetime.timedelta(days=365)  # today.replace(year=today.year - 1) fails for leap years

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

        if hasattr(self.request.user, "player"):
            context["is_rival"] = self.request.user.player.rivals.filter(id=player_id).exists()

        context["wrapped_years"] = range(player.join_date.year, today.year + 1)

        return context

    def get_queryset(self):
        player_id = self.kwargs["player_id"]
        player = Player.get_or_404(id=player_id)

        return player.scores.order_by("-submission_date").prefetch_related("song")


class PlayerHighscoresView(PlayerView):
    def get_queryset(self):
        player_id = self.kwargs["player_id"]
        player = Player.get_or_404(id=player_id)

        return (
            player.scores.filter(**{f"is_{self.lb_source}_top": True})
            .order_by(f"-{self.lb_attribute}")
            .prefetch_related("song")
        )


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
        scores = player.scores.filter(is_itg_top=True, song__hash__in=songs).prefetch_related("song")

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
        context["num_charts_played"] = scores.filter(is_itg_top=True).count()
        set_stars(context, scores)

        return context


class VersusView(LeaderboardSourceMixin, generic.ListView):
    template_name = "boogie_ui/versus.html"

    def sort_key(self, x):
        return getattr(x[0], self.lb_attribute)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        p1, p2 = self.get_players()
        p1_scores_qs = (
            p1.scores.filter(**{f"is_{self.lb_source}_top": True}).order_by("-itg_score").all().select_related("song")
        )
        p2_scores_qs = p2.scores.filter(
            **{f"is_{self.lb_source}_top": True}, song__hash__in=[score.song_id for score in p1_scores_qs]
        )
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
        context["p1_num_charts_played"] = p1.scores.filter(is_itg_top=True).count()
        context["p1_wins"] = sum(
            (1 for x in scores if getattr(x[0], self.lb_attribute) > getattr(x[1], self.lb_attribute))
        )
        set_stars(context, p1.scores, prefix="p1_")

        context["p2_num_scores"] = p2.scores.count()
        context["p2_num_charts_played"] = p2.scores.filter(is_itg_top=True).count()
        context["p2_wins"] = sum(
            (1 for x in scores if getattr(x[0], self.lb_attribute) < getattr(x[1], self.lb_attribute))
        )
        set_stars(context, p2.scores, prefix="p2_")

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
        return getattr(x[0], self.lb_attribute) - getattr(x[1], self.lb_attribute)


class SongView(LeaderboardSourceMixin, generic.ListView):
    template_name = "boogie_ui/song.html"
    context_object_name = "scores"
    paginate_by = ENTRIES_PER_PAGE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        song_hash = self.kwargs["song_hash"]
        song = Song.get_or_404(hash=song_hash)
        context["song"] = song
        context["num_highscores"] = song.scores.filter(is_itg_top=True).count()
        if hasattr(self.request.user, "player"):
            context["my_scores"] = song.scores.filter(player=self.request.user.player).count()

        if player_id := self.kwargs.get("player_id"):
            context["player"] = Player.get_or_404(id=player_id)

        return context

    def get_queryset(self):
        song_hash = self.kwargs["song_hash"]
        return (
            Song.get_or_404(hash=song_hash)
            .scores.order_by(f"-{self.lb_attribute}", "submission_date")
            .select_related("song", "player")
        )


class SongByDateView(SongView):
    def get_queryset(self):
        song_hash = self.kwargs["song_hash"]
        return (
            Song.get_or_404(hash=song_hash)
            .scores.order_by("-submission_date", f"-{self.lb_attribute}")
            .select_related("song", "player")
        )


class ScoreView(LeaderboardSourceMixin, generic.DetailView):
    template_name = "boogie_ui/score.html"
    model = Score


class SongHighscoresView(SongView):
    def get_queryset(self):
        song_hash = self.kwargs["song_hash"]
        return (
            Song.get_or_404(hash=song_hash)
            .scores.filter(**{f"is_{self.lb_source}_top": True})
            .order_by(f"-{self.lb_attribute}", "submission_date")
            .select_related("song", "player")
        )


class SongByPlayerView(SongView):
    def get_queryset(self):
        player = Player.get_or_404(id=self.kwargs["player_id"])
        song = Song.get_or_404(hash=self.kwargs["song_hash"])
        return (
            song.scores.filter(player=player)
            .order_by(f"-{self.lb_attribute}", "submission_date")
            .select_related("song", "player")
        )


class SongsListView(LeaderboardSourceMixin, generic.ListView):
    template_name = "boogie_ui/songs.html"
    context_object_name = "songs"
    paginate_by = ENTRIES_PER_PAGE

    def get_queryset(self):
        return Song.objects.order_by("-number_of_scores").prefetch_related(
            f"{self.lb_source}_highscore",
            f"{self.lb_source}_highscore__player",
        )


class SongsByPlayersListView(SongsListView):
    def get_queryset(self):
        return Song.objects.order_by("-number_of_players").prefetch_related(
            f"{self.lb_source}_highscore", f"{self.lb_source}_highscore__player"
        )


class SuccessMessageExtraTagsMixin:
    success_message = ""
    success_message_extra_tags = ""

    def form_valid(self, form):
        response = super().form_valid(form)
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message, extra_tags=self.success_message_extra_tags)
        return response

    def get_success_message(self, cleaned_data):
        return self.success_message % cleaned_data


class EditPlayerView(LoginRequiredMixin, SuccessMessageExtraTagsMixin, generic.UpdateView):
    login_url = "/login/"
    template_name = "boogie_ui/player_update.html"
    form_class = EditPlayerForm
    success_message = "Profile updated successfully!"
    success_message_extra_tags = "alert-success"

    def get_object(self, **kwargs):
        return self.request.user.player

    def get_success_url(self):
        return reverse("edit")


class MyProfileView(LoginRequiredMixin, generic.RedirectView):
    login_url = "/login/"

    def get_redirect_url(self, *args, **kwargs):
        player_id = self.request.user.player.id
        return reverse("player", kwargs={"player_id": player_id})


@require_POST
@login_required(login_url="/login/")
def add_rival(request, player_id):
    target_player: Player = Player.get_or_404(id=player_id)
    myself: Player = request.user.player
    myself.rivals.add(player_id)
    myself.save()
    messages.success(
        request,
        f"Added {target_player.name} to your rivals.",
        extra_tags="alert-success",
    )
    return redirect("player", player_id=player_id)


@require_POST
@login_required(login_url="/login/")
def remove_rival(request, player_id):
    target_player: Player = Player.get_or_404(id=player_id)
    myself: Player = request.user.player
    myself.rivals.remove(player_id)
    myself.save()
    messages.success(
        request,
        f"Removed {target_player.name} from your rivals.",
        extra_tags="alert-success",
    )
    return redirect("player", player_id=player_id)


def login_user(request):
    response_status = OK

    if request.POST:
        gs_api_key = request.POST["gs_api_key"]

        user = authenticate(request, gs_api_key=gs_api_key)
        if user is not None:
            login(request, user)
            messages.success(request, "Signed-in successfully.", extra_tags="alert-success")
            return HttpResponseRedirect(request.POST.get("next") or "/")
        else:
            messages.error(
                request,
                "Invalid GS API Key, please try again."
                " This can also mean that you don't have a BoogieStats account yet."
                " Please submit the first score to create an account."
                f""" Consult the <a href="{reverse("manual")}">User Manual</a> for more information.""",
                extra_tags="alert-danger",
            )
            response_status = UNAUTHORIZED

    next = request.GET.get("next") or request.POST.get("next")
    return render(request, template_name="boogie_ui/login.html", context={"next": next}, status=response_status)


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

    q_and_a = {
        "Will the scores be saved to GrooveStats when I use BoogieStats?": f"""Yes! BoogieStats acts as a proxy for GrooveStats. It records all received scores and also passes them to GrooveStats. You can select which leaderboards you want to see in game in your <a href="{reverse("edit")}">Profile</a>.""",
        """How to enable EX Score leaderboards?""": f"""Go to <a href="{reverse("edit")}">Edit Profile</a> page and select <code>BoogieStats EX Scores</code> from the <code>Leaderboard source</code> drop-down list and and click <code>Update</code> to enable EX Scores for the in-game leaderboards. UI has a toggle for ITG/EX Scores in the navbar at the top.""",  # nosec
        "Is it safe?": """It's probably as safe as using a USB Profile on a public machine in an arcade or during a convention. I don't store your GrooveStats API key in a clear form, and the whole key is used only during forwarding scores to GrooveStats. You can inspect the code <a href="https://github.com/florczakraf/boogie-stats" target="_blank">on GitHub</a> or host the app for yourself if you don't plan to use the comparison & leaderboards features.""",
        "What if I play a song that's not in your database?": """BoogieStats will automatically accept and track its scores. It will look like any other ranked song in your game. In the UI, the song will display a song hash instead of a title until its information is added to the <a href="https://github.com/florczakraf/stepmania-chart-db" target="_blank">public chart database</a>. Please send me a list of packs that are missing when you encounter this issue. Once the song metadata is added to the database, the UI will show it for the scores sent in the past as well.""",
        "Will you support <code>Stats.xml</code> or <code>simply.training</code> jsons?": "Not in the current form. They don't use the unique song identifiers, therefore BoogieStats is not going to try and match songs by their paths, which has already been proven by GrooveStats to be a tedious, troublesome and ambiguous.",
        "Do events held by GrooveStats and the related leaderboards work with BoogieStats?": """ITL and SRPG as well as their custom leaderboards are supported. As for the other events, it's probably a matter of a little time if they introduce a custom API.""",
        "Will it work in a public arcade with a USB Profile?": """Yes, as long as the machine is set up to use BoogieStats. If you run a public machine, please let your players know that their GrooveStats API key would be exposed to a 3rd-party proxy.""",
        "I generated a new API Key, now what?": f"""Don't panic and please don't send any scores before updating your BoogieStats profile. Use your <b>old</b> Api Key to log in to <a href="{reverse("edit")}">Edit Profile</a> page and paste the <b>new</b> key into <code>New GrooveStats API key</code> field and click <code>Update</code>. You can now send scores using the new API Key.""",
        "I already sent a score with a new API Key and there are two profiles on the site, now what?": """Currently there's no way to merge profiles, but it's <a href="https://github.com/florczakraf/boogie-stats/issues/84">planned for the future</a>. Please keep your old API Key saved somewhere so that you can claim your profile and scores later in the future.""",
        "How can I support the development of the project?": """If you spot a bug or would like to request a new functionality, please <a href="https://github.com/florczakraf/boogie-stats/issues" target="_blank">create an issue on project's GitHub page.</a> Source code contributions are also welcome, please create an issue before submitting a Pull Request so we can talk about it first.""",
    }

    q_and_a.update(settings.BS_EXTRA_Q_AND_A)

    return render(
        request,
        template_name="boogie_ui/manual.html",
        context={
            "boogiestats_allow_host": boogiestats_allow_host,
            "boogiestats_url_prefix": boogiestats_url_prefix,
            "q_and_a": q_and_a,
        },
    )


class SearchView(LeaderboardSourceMixin, generic.ListView):
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
        set_sentry_user(self.request)

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
            .prefetch_related(
                f"{self.lb_source}_highscore",
                f"{self.lb_source}_highscore__player",
            )
            .order_by("-num_scores", f"-{self.lb_source}_highscore__{self.lb_source}_score")
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


class PlayerWrappedView(generic.base.TemplateView):
    template_name = "boogie_ui/player_wrapped.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        player_id = self.kwargs["player_id"]
        year = self.kwargs["year"]
        player = Player.get_or_404(id=player_id)
        context["player"] = player
        context["year"] = year
        scores = player.scores.filter(submission_date__year=year)
        context["num_scores"] = scores.count()
        context["num_charts_played"] = scores.filter(is_itg_top=True).count()
        set_stars(context, scores)

        end_of_year = datetime.date(year=year, month=12, day=31)
        start_of_year = datetime.date(year=year, month=1, day=1)

        context["skip_days_range"] = range(start_of_year.timetuple().tm_wday)

        context["start_date"] = start_of_year
        played_days = (
            player.scores.values("submission_day")
            .filter(submission_day__year=year)
            .annotate(plays=Count("submission_day"))
            .all()
        )
        context["months"] = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        context["days"] = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        context["calendar_legend"] = tuple(
            [("0", "min-plays-0")] + [(f"{number}+", f"min-plays-{number}") for number in CALENDAR_VALUES]
        )
        calendar_days = list(
            {"class": "min-plays-0", "plays": 0, "day": start_of_year + datetime.timedelta(days=i)}
            for i in range((end_of_year - start_of_year).days + 1)
        )
        context["calendar_days"] = calendar_days

        if not context["num_scores"]:
            return context
        most_played_song_data = scores.values("song_id").annotate(plays=Count("song_id")).order_by("-plays").first()
        most_played_song = Song.objects.get(hash=most_played_song_data["song_id"])
        most_played_song_plays = most_played_song_data["plays"]

        previous_day = (played_days[0]["submission_day"] - start_of_year).days
        streak = 1
        longest_streak = 1
        first_day = first_day_candidate = played_days[0]
        for day in played_days:
            day_index = (day["submission_day"] - start_of_year).days

            if previous_day == day_index - 1:
                previous_day = day_index
                streak += 1
                if streak > longest_streak:
                    longest_streak = streak
                    first_day = first_day_candidate
            else:
                previous_day = day_index
                first_day_candidate = day
                streak = 1

            plays = day["plays"]
            calendar_days[day_index]["plays"] = plays
            calendar_days[day_index]["class"] = plays_to_class(plays)

        context["played_days"] = len(played_days)
        context["most_plays"] = max(played_days, key=lambda x: x["plays"], default={"plays": 0, "submission_day": "-"})
        context["longest_streak"] = longest_streak
        if first_day is not None:
            context["longest_streak_start"] = first_day["submission_day"]
        context["most_played_song"] = most_played_song
        context["most_played_song_plays"] = most_played_song_plays
        context["highest_itg_score"] = scores.order_by("-itg_score", "submission_date").first()
        context["highest_ex_score"] = scores.order_by("-ex_score", "submission_date").first()
        context["wrapped_years"] = range(player.join_date.year, datetime.date.today().year + 1)

        return context
