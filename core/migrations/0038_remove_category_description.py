# Generated by Django 4.1 on 2022-09-03 21:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0037_remove_project_description"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="category",
            name="description",
        ),
    ]
