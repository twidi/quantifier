# Generated by Django 4.1 on 2022-08-10 11:14

import django.core.validators
from django.db import migrations, models
import re


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0034_project_quantity_name_help_text"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="quick_add_quantities",
            field=models.TextField(
                blank=True,
                help_text="A list of quantities available as quick add buttons. Each quantity is separated by a comma. Example: 1,2,5,10,20,50,100",
                validators=[
                    django.core.validators.RegexValidator(
                        re.compile("^(\\s*\\d+\\s*,)*\\s*\\d+\\s*$"),
                        code="invalid",
                        message="Enter only digits separated by commas.",
                    )
                ],
            ),
        ),
    ]
