# Generated by Django 4.1b1 on 2022-07-07 17:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_add_project_quantity_constraint_and_name"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="project",
            name="core_project_interval_quantity_null_in_reverse_mode",
        ),
        migrations.AlterField(
            model_name="project",
            name="interval",
            field=models.CharField(
                choices=[
                    ("daily", "daily"),
                    ("weekly", "weekly"),
                    ("monthly", "monthly"),
                    ("none", "none"),
                ],
                default="none",
                max_length=10,
            ),
        ),
        migrations.AddConstraint(
            model_name="project",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("reverse_mode", True), ("interval_quantity__isnull", True)),
                    models.Q(("reverse_mode", False), ("interval_quantity__isnull", False)),
                    _connector="OR",
                ),
                name="core_project_interval_quantity_null_in_reverse_mode",
                violation_error_message="Quantity must not be set in reverse mode",
            ),
        ),
    ]
