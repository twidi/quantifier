# Generated by Django 4.1 on 2022-09-05 00:38

import core.fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0042_quantity_datetime_to_date"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="quantity",
            options={"ordering": ["-date", "-time"], "verbose_name_plural": "quantities"},
        ),
        migrations.RemoveIndex(
            model_name="quantity",
            name="core_quanti_categor_52f76d_idx",
        ),
        migrations.RemoveField(
            model_name="quantity",
            name="datetime",
        ),
        migrations.AddIndex(
            model_name="quantity",
            index=models.Index(fields=["category", "date", "time"], name="core_quanti_categor_52f76d_idx"),
        ),
    ]
