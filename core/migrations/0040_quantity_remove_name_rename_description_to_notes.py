# Generated by Django 4.1 on 2022-09-03 21:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0039_merge_quantity_name_and_description"),
    ]

    operations = [
        migrations.RenameField(
            model_name="quantity",
            old_name="description",
            new_name="notes",
        ),
        migrations.RemoveField(
            model_name="quantity",
            name="name",
        ),
    ]
