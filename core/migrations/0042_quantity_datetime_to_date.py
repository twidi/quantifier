# Generated by Django 4.1 on 2022-09-05 00:29
from datetime import datetime

import django.utils.timezone
from django.db import migrations, models


def datetime_to_date(apps, schema_editor):
    """Convert all datetime fields to date fields."""
    Quantity = apps.get_model("core", "Quantity")
    for quantity in Quantity.objects.all():
        quantity.date = quantity.datetime.date()
        quantity.time = quantity.datetime.time()
        quantity.save()


def date_to_datetime(apps, schema_editor):
    """Convert all date fields to datetime fields."""
    Quantity = apps.get_model("core", "Quantity")
    for quantity in Quantity.objects.all():
        quantity.datetime = datetime.combine(quantity.date, quantity.time or datetime.min.time())
        quantity.save()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0041_text_for_project_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="quantity",
            name="date",
            field=models.DateField(
                default=django.utils.timezone.now,
            ),
        ),
        migrations.AddField(
            model_name="quantity",
            name="time",
            field=models.TimeField(
                blank=True,
                null=True,
            ),
        ),
        migrations.RunPython(datetime_to_date, date_to_datetime),
    ]
