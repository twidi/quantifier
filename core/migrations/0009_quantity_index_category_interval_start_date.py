# Generated by Django 4.1b1 on 2022-07-08 00:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_quantity_start_end_dates_constraint"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="quantity",
            index=models.Index(
                fields=["category", "interval_start_date"],
                name="core_quanti_categor_150206_idx",
            ),
        ),
    ]
