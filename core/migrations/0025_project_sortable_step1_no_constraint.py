# Generated by Django 4.1b1 on 2022-08-07 01:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0024_add_alltime_to_intervals"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="sort_order",
            field=models.IntegerField(blank=True, db_index=True, default=0),
            preserve_default=False,
        ),
    ]
