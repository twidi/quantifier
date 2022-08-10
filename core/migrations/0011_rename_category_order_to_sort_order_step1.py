# Generated by Django 4.1b1 on 2022-07-08 11:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_quantity_interval_nullable"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="category",
            options={"ordering": ["sort_order"], "verbose_name_plural": "categories"},
        ),
        migrations.RemoveConstraint(
            model_name="category",
            name="core_category_name_no_parent_uniq",
        ),
        migrations.RemoveConstraint(
            model_name="category",
            name="core_category_name_parent_uniq",
        ),
        migrations.RemoveConstraint(
            model_name="category",
            name="core_category_order_no_parent_uniq",
        ),
        migrations.RemoveConstraint(
            model_name="category",
            name="core_category_order_parent_uniq",
        ),
        migrations.RenameField(
            model_name="category",
            old_name="order",
            new_name="sort_order",
        ),
    ]
