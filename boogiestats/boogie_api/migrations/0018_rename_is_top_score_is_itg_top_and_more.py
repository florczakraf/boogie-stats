# Generated by Django 4.2.3 on 2023-08-04 20:51

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("boogie_api", "0017_player_leaderboard_source"),
    ]

    operations = [
        migrations.RenameField(
            model_name="score",
            old_name="is_top",
            new_name="is_itg_top",
        ),
        migrations.RenameField(
            model_name="score",
            old_name="score",
            new_name="itg_score",
        ),
        migrations.RenameField(
            model_name="song",
            old_name="highscore",
            new_name="itg_highscore",
        ),
    ]
