from django.urls import reverse


def test_successful_login(client, player):
    response = client.post(reverse("login"), data={"gs_api_key": "playerkey"}, follow=True)

    assert response.status_code == 200
    assert "Signed-in successfully" in response.content.decode()


def test_failed_login(client, player):
    response = client.post(reverse("login"), data={"gs_api_key": "non-existent"}, follow=True)

    assert response.status_code == 401
    assert "Invalid GS API Key" in response.content.decode()


def test_managing_rivals_requires_login(client, player, rival1):
    response = client.post(reverse("remove_rival", kwargs={"player_id": rival1.id}), follow=True)

    assert response.request["PATH_INFO"] == reverse("login")
    assert player.rivals.filter(id=rival1.id).exists()


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
