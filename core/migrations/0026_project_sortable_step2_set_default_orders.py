# Generated by Django 4.1b1 on 2022-08-07 01:50

from django.db import migrations


def set_default_orders(apps, schema_editor):
    User = apps.get_model("core", "User")
    for user in User.objects.all():
        for index, project in enumerate(user.projects.all().order_by("id")):
            project.sort_order = index + 1
            project.save()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0025_project_sortable_step1_no_constraint"),
    ]

    operations = [
        migrations.RunPython(
            set_default_orders,
            migrations.RunPython.noop,
        )
    ]
