from django.db import migrations


def create_identities_for_existing_players(apps, schema_editor):
    Player = apps.get_model("boogie_api", "Player")
    PlayerIdentity = apps.get_model("boogie_api", "PlayerIdentity")

    identities = [
        PlayerIdentity(provider="gs_api_key", external_id=player.api_key, player_id=player.pk)
        for player in Player.objects.all().iterator()
    ]
    PlayerIdentity.objects.bulk_create(identities, batch_size=1000, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ("boogie_api", "0029_playeridentity"),
    ]

    operations = [
        migrations.RunPython(create_identities_for_existing_players, migrations.RunPython.noop),
    ]
