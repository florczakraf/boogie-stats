import importlib.util
import pathlib

import pytest
from django.apps import apps as global_apps
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from boogiestats.boogie_api.choices import GSIntegration, IdentityProvider
from boogiestats.boogie_api.models import Player, PlayerIdentity, Score
from boogiestats.boogie_api.views import get_or_create_player

MIGRATION_NAME = "0030_backfill_playeridentities"


def load_backfill_function():
    migrations_dir = pathlib.Path(__file__).parents[1] / "migrations"
    spec = importlib.util.spec_from_file_location(
        f"boogiestats.boogie_api.migrations.{MIGRATION_NAME}", migrations_dir / f"{MIGRATION_NAME}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.create_identities_for_existing_players


@pytest.fixture
def player():
    return Player.objects.create(gs_api_key="playerkey", machine_tag="PL")


class TestPlayerCreationCreatesIdentity:
    def test_creating_player_creates_its_first_identity(self, player):
        identity = player.identities.get()
        assert identity.provider == IdentityProvider.GS_API_KEY
        key = Player.gs_api_key_to_bs_api_key("playerkey")
        assert identity.external_id == key
        assert identity.player == player
        assert identity.player.api_key == key

    def test_all_players_have_at_least_one_identity(self, player):
        other = Player.objects.create(gs_api_key="otherkey", machine_tag="OT")

        assert PlayerIdentity.objects.filter(player=player).exists()
        assert PlayerIdentity.objects.filter(player=other).exists()


class TestNoOrphanPlayers:
    def test_failed_identity_creation_does_not_orphan_a_player(self, monkeypatch):
        """If the identity insert fails (e.g. a concurrent request with the same
        new key won the race and inserted the identity first), the player row
        must not survive without any identity."""

        def boom(self, *args, **kwargs):
            raise IntegrityError("duplicate identity")

        monkeypatch.setattr(PlayerIdentity, "save", boom)

        with pytest.raises(IntegrityError):
            get_or_create_player("brandnewkey")

        assert not Player.objects.filter(identities__isnull=True)


class TestLookupByIdentity:
    def test_get_by_gs_api_key_returns_the_player(self, player):
        assert PlayerIdentity.get_by_gs_api_key("playerkey") == player

    def test_get_by_gs_api_key_for_unknown_key_returns_none(self, player):
        assert PlayerIdentity.get_by_gs_api_key("non-existent") is None

    def test_lookup_after_key_rotation_returns_the_same_player(self, player):
        player.identities.create(
            provider=IdentityProvider.GS_API_KEY, external_id=Player.gs_api_key_to_bs_api_key("newkey")
        )

        assert PlayerIdentity.get_by_gs_api_key("newkey") == player
        assert PlayerIdentity.get_by_gs_api_key("playerkey") == player


class TestConstraints:
    # use bulk_create to bypass full_clean and hit the DB constraints directly
    def test_same_provider_and_external_id_cannot_be_created_twice(self, player):
        external_id = Player.gs_api_key_to_bs_api_key("playerkey")

        with pytest.raises(IntegrityError):
            PlayerIdentity.objects.bulk_create(
                [PlayerIdentity(player=player, provider=IdentityProvider.GS_API_KEY, external_id=external_id)]
            )

    def test_the_same_external_id_is_allowed_for_different_providers(self, player):
        external_id = Player.gs_api_key_to_bs_api_key("playerkey")

        PlayerIdentity.objects.bulk_create(
            [PlayerIdentity(player=player, provider="other_provider", external_id=external_id)]
        )

        assert PlayerIdentity.objects.filter(external_id=external_id).count() == 2


class TestExternalIdLength:
    # 255 is the max length of an OIDC `sub` claim, i.e. the ceiling for OAuth-based providers
    def test_external_id_can_be_255_chars_long(self, player):
        external_id = "x" * 255

        identity = PlayerIdentity.objects.create(
            player=player, provider=IdentityProvider.GS_API_KEY, external_id=external_id
        )

        assert identity.pk is not None

    def test_external_id_cannot_be_longer_than_255_chars(self, player):
        with pytest.raises(ValidationError):
            PlayerIdentity.objects.create(player=player, provider=IdentityProvider.GS_API_KEY, external_id="x" * 256)


class TestReadPathsGoThroughIdentities:
    def test_auth_backend_authenticates_by_identity(self, player):
        user = authenticate(request=None, gs_api_key="playerkey")

        assert user == player.user

    def test_auth_backend_for_unknown_key_returns_none(self, player):
        assert authenticate(request=None, gs_api_key="non-existent") is None

    def test_auth_backend_works_for_rotated_key(self, player):
        player.identities.create(
            provider=IdentityProvider.GS_API_KEY, external_id=Player.gs_api_key_to_bs_api_key("newkey")
        )

        assert authenticate(request=None, gs_api_key="newkey") == player.user
        assert authenticate(request=None, gs_api_key="playerkey") == player.user

    def test_auth_backend_rejects_retired_key(self, player):
        player.identities.get().delete()

        assert authenticate(request=None, gs_api_key="playerkey") is None

    def test_score_submission_with_rotated_key_lands_on_the_same_player(self, client, player):
        player.gs_integration = GSIntegration.SKIP
        player.save()
        new_key = "ffffffffffffffff" * 4
        player.identities.create(
            provider=IdentityProvider.GS_API_KEY, external_id=Player.gs_api_key_to_bs_api_key(new_key)
        )

        response = client.post(
            "/score-submit.php?chartHashP1=0123456789ABCDEF&maxLeaderboardResults=3",
            data={"player1": {"score": 5000, "comment": "foo", "rate": 100}},
            content_type="application/json",
            HTTP_x_api_key_player_1=new_key,
        )

        assert response.status_code == 200
        assert Score.objects.count() == 1
        assert Score.objects.get().player == player


class TestDataMigration:
    def test_backfill_creates_one_identity_per_player(self, player, db):
        # simulate a pre-identity row: api_key populated, no identities
        legacy_api_key = Player.gs_api_key_to_bs_api_key("playerkey")
        Player.objects.filter(pk=player.pk).update(api_key=legacy_api_key)
        PlayerIdentity.objects.all().delete()
        create_identities_for_existing_players = load_backfill_function()

        create_identities_for_existing_players(global_apps, None)

        identity = player.identities.get()
        assert identity.provider == "gs_api_key"
        assert identity.external_id == legacy_api_key

    def test_backfill_is_idempotent(self, player):
        create_identities_for_existing_players = load_backfill_function()

        create_identities_for_existing_players(global_apps, None)
        create_identities_for_existing_players(global_apps, None)

        assert player.identities.count() == 1
