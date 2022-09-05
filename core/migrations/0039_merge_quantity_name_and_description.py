# Generated by Django 4.1 on 2022-09-03 21:08

from django.db import migrations


def merge_fields(apps, schema_editor):
    """Merge the name and description fields into a single field, with a new line between them, only if the name is set."""
    Quantity = apps.get_model("core", "Quantity")
    for quantity in Quantity.objects.all():
        if quantity.name:
            quantity.description = (
                f"{quantity.name}\n\n{quantity.description}" if quantity.description else quantity.name
            )
            quantity.save()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0038_remove_category_description"),
    ]

    operations = [
        migrations.RunPython(
            merge_fields,
            migrations.RunPython.noop,
        )
    ]
