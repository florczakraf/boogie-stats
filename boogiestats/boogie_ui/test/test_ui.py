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


NEW_KEY = "newkeynewkeynewkeynewkeynewkeyne"


def test_add_identity_attaches_a_second_key(client, player):
    client.force_login(player.user)

    response = client.post(reverse("add_identity"), data={"gs_api_key": NEW_KEY}, follow=True)

    assert response.status_code == 200
    assert "API key attached to your profile." in response.content.decode()
    assert player.identities.count() == 2
    assert PlayerIdentity.get_by_gs_api_key(NEW_KEY) == player
    assert PlayerIdentity.get_by_gs_api_key("playerkey") == player  # old key still works


def test_add_identity_requires_login(client, player):
    response = client.post(reverse("add_identity"), data={"gs_api_key": NEW_KEY}, follow=True)

    assert response.request["PATH_INFO"] == reverse("login")
    assert player.identities.count() == 1


def test_add_identity_rejects_bad_key(client, player):
    client.force_login(player.user)

    response = client.post(reverse("add_identity"), data={"gs_api_key": "too-short"}, follow=True)

    assert "API key attached to your profile." not in response.content.decode()
    assert player.identities.count() == 1


def test_add_identity_rejects_duplicate_key(client, player):
    client.force_login(player.user)
    player.identities.create(provider=IdentityProvider.GS_API_KEY, external_id=Player.gs_api_key_to_bs_api_key(NEW_KEY))

    response = client.post(reverse("add_identity"), data={"gs_api_key": NEW_KEY}, follow=True)

    assert "already attached to your profile." in response.content.decode()
    assert player.identities.count() == 2


OTHER_KEY = "otherkeyotherkeyotherkeyotherkey"


def test_add_identity_rejects_key_used_by_other_player(client, player, rival1):
    client.force_login(player.user)
    rival1.identities.create(
        provider=IdentityProvider.GS_API_KEY, external_id=Player.gs_api_key_to_bs_api_key(OTHER_KEY)
    )

    response = client.post(
        reverse("add_identity"),
        data={"gs_api_key": OTHER_KEY},
        follow=True,
    )

    assert "already used by another profile." in response.content.decode()
    assert player.identities.count() == 1


def test_remove_identity_retires_the_key(client, player):
    client.force_login(player.user)
    identity = player.identities.create(
        provider=IdentityProvider.GS_API_KEY, external_id=Player.gs_api_key_to_bs_api_key(NEW_KEY)
    )

    response = client.post(reverse("remove_identity", kwargs={"identity_id": identity.id}), follow=True)

    assert response.status_code == 200
    assert "API key removed from your profile." in response.content.decode()
    assert player.identities.count() == 1
    assert PlayerIdentity.get_by_gs_api_key(NEW_KEY) is None
    assert PlayerIdentity.get_by_gs_api_key("playerkey") == player


def test_cannot_remove_the_last_identity(client, player):
    client.force_login(player.user)
    identity = player.identities.get()

    response = client.post(reverse("remove_identity", kwargs={"identity_id": identity.id}), follow=True)

    assert "You can't remove your last API key" in response.content.decode()
    assert player.identities.count() == 1


def test_cannot_remove_someone_elses_identity(client, player, rival1):
    client.force_login(player.user)
    foreign_identity = rival1.identities.get()

    response = client.post(reverse("remove_identity", kwargs={"identity_id": foreign_identity.id}), follow=True)

    # POST + Http404 → the project's TemplateView-based 404 handler responds with 405
    assert response.status_code == 405
    assert rival1.identities.count() == 1


def test_edit_form_does_not_touch_identities(player):
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
