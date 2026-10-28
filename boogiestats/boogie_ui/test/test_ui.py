import pytest
from django.urls import reverse

from boogiestats.boogie_api.choices import (
    GSIntegration,
    IdentityProvider,
    LeaderboardSource,
)
from boogiestats.boogie_api.models import GSStatus, Player, PlayerIdentity, Score
from boogiestats.boogie_ui.forms import EditPlayerForm


def test_successful_login(client, player):
    response = client.post(reverse("login"), data={"gs_api_key": "playerkey"}, follow=True)

    assert response.status_code == 200
    assert "Signed-in successfully" in response.content.decode()


def test_failed_login(client, player):
    response = client.post(reverse("login"), data={"gs_api_key": "non-existent"}, follow=True)

    assert response.status_code == 401
    assert "Invalid GS API Key" in response.content.decode()


def test_changing_gs_api_key_rotates_the_identity(player):
    form = EditPlayerForm(
        data={
            "machine_tag": "PL",
            "name": "PL",
            "gs_integration": GSIntegration.REQUIRE,
            "leaderboard_source": LeaderboardSource.BS,
            "gs_api_key": "newkeynewkeynewkeynewkeynewkeyne",
            "rivals": [],
        },
        instance=player,
    )

    assert form.is_valid()
    form.save()

    assert player.identities.count() == 1
    identity = player.identities.get()
    assert identity.provider == IdentityProvider.GS_API_KEY
    assert identity.external_id == Player.gs_api_key_to_bs_api_key("newkeynewkeynewkeynewkeynewkeyne")
    assert PlayerIdentity.get_by_gs_api_key("newkeynewkeynewkeynewkeynewkeyne") == player
    assert PlayerIdentity.get_by_gs_api_key("playerkey") is None  # old key retired


def test_edit_form_without_new_key_keeps_the_identity(player):
    form = EditPlayerForm(
        data={
            "machine_tag": "XX",
            "name": "XX",
            "gs_integration": GSIntegration.REQUIRE,
            "leaderboard_source": LeaderboardSource.BS,
            "rivals": [],
        },
        instance=player,
    )

    assert form.is_valid()
    form.save()

    assert player.identities.count() == 1
    assert PlayerIdentity.get_by_gs_api_key("playerkey") == player


def test_managing_rivals_requires_login(client, player, rival1):
    response = client.post(reverse("remove_rival", kwargs={"player_id": rival1.id}), follow=True)

    assert response.request["PATH_INFO"] == reverse("login")
    player.refresh_from_db()
    assert player.rivals.filter(id=rival1.id).exists()

    player.rivals.remove(rival1)
    player.save()

    response = client.post(reverse("add_rival", kwargs={"player_id": rival1.id}), follow=True)
    assert response.request["PATH_INFO"] == reverse("login")
    player.refresh_from_db()
    assert not player.rivals.filter(id=rival1.id).exists()


def test_managing_rivals(client, player, rival1):
    client.force_login(player.user)
    assert player.rivals.filter(id=rival1.id).exists()

    response = client.post(reverse("remove_rival", kwargs={"player_id": rival1.id}), follow=True)
    assert response.status_code == 200
    assert "Removed RIV1 from your rivals" in response.content.decode()

    player.refresh_from_db()
    assert not player.rivals.filter(id=rival1.id).exists()

    response = client.post(reverse("add_rival", kwargs={"player_id": rival1.id}), follow=True)
    assert response.status_code == 200
    assert "Added RIV1 to your rivals" in response.content.decode()

    player.refresh_from_db()
    assert player.rivals.filter(id=rival1.id).exists()


@pytest.mark.parametrize(
    ["is_owner_logged_in", "gs_status", "are_buttons_expected"],
    [
        (True, GSStatus.OK, False),
        (True, GSStatus.ERROR, True),
        (True, GSStatus.SKIPPED, True),
        (False, GSStatus.OK, False),
        (False, GSStatus.ERROR, False),
        (False, GSStatus.SKIPPED, False),
    ],
)
def test_show_gs_submission_buttons(client, player, is_owner_logged_in, gs_status, are_buttons_expected):
    score: Score = player.scores.first()
    score.gs_status = gs_status
    score.save()

    if is_owner_logged_in:
        client.force_login(player.user)

    response = client.get(reverse("score", kwargs={"pk": score.pk}))

    assert gs_status.label in response.content.decode()
    assert ("Submit to GS" in response.content.decode()) is are_buttons_expected
    assert ("Mark as successfully submitted" in response.content.decode()) is are_buttons_expected


def test_marking_score_as_submitted_to_gs_requires_login(client, player):
    score: Score = player.scores.first()
    score.gs_status = GSStatus.ERROR
    score.save()

    response = client.post(reverse("mark_score_as_gs_submitted", kwargs={"pk": score.pk}), follow=True)
    score.refresh_from_db()

    assert response.request["PATH_INFO"] == reverse("login")
    assert score.gs_status == GSStatus.ERROR


def test_marking_score_as_submitted_to_gs_for_fails_for_not_owned_scores(client, player, rival1):
    score: Score = player.scores.first()
    score.gs_status = GSStatus.ERROR
    score.save()

    client.force_login(rival1.user)
    response = client.post(reverse("mark_score_as_gs_submitted", kwargs={"pk": score.pk}), follow=True)
    score.refresh_from_db()

    assert response.request["PATH_INFO"] == reverse("score", kwargs={"pk": score.pk})
    assert score.gs_status == GSStatus.ERROR
    assert "You can only modify your own scores" in response.content.decode()


def test_marking_score_as_submitted_to_gs_for_owned_scores(client, player):
    score: Score = player.scores.first()
    score.gs_status = GSStatus.ERROR
    score.save()

    client.force_login(player.user)
    response = client.post(reverse("mark_score_as_gs_submitted", kwargs={"pk": score.pk}), follow=True)
    score.refresh_from_db()

    assert response.request["PATH_INFO"] == reverse("score", kwargs={"pk": score.pk})
    assert score.gs_status == GSStatus.OK
    assert "Score marked as successfully submitted to GS" in response.content.decode()
