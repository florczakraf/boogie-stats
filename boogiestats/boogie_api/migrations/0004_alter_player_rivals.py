# Generated by Django 4.0.4 on 2022-05-22 20:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("boogie_api", "0003_auto_20220522_1934"),
    ]

    operations = [
        migrations.AlterField(
            model_name="player",
            name="rivals",
            field=models.ManyToManyField(blank=True, to="boogie_api.player"),
        ),
    ]