# Generated by Django 5.0.3 on 2024-04-14 15:04

from django.db import migrations, models


def fill_stars(apps, schema_editor):
    Player = apps.get_model("boogie_api", "Player")
    for player in Player.objects.all():
        scores = player.scores
        player.one_star = scores.filter(is_itg_top=True, itg_score__gte=9600, itg_score__lt=9800).count()
        player.two_stars = scores.filter(is_itg_top=True, itg_score__gte=9800, itg_score__lt=9900).count()
        player.three_stars = scores.filter(is_itg_top=True, itg_score__gte=9900, itg_score__lt=10000).count()
        player.four_stars = player.scores.filter(is_itg_top=True, itg_score=10000).count()
        player.five_stars = player.scores.filter(is_ex_top=True, ex_score=10000).count()

        player.save()


class Migration(migrations.Migration):
    dependencies = [
        ("boogie_api", "0023_alter_player_machine_tag_alter_player_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="player",
            name="five_stars",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name="player",
            name="four_stars",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name="player",
            name="one_star",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name="player",
            name="three_stars",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name="player",
            name="two_stars",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.RunPython(fill_stars),
    ]
