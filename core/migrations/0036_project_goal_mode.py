# Generated by Django 4.1 on 2022-08-11 23:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0035_allow_spaces_in_quick_add_qtt"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="goal_mode",
            field=models.BooleanField(
                default=False,
                help_text="By default the limit quantity (and planned amounts in categories) are a maximum not to be exceeded. By checking this, the behavior is inverted: these values are a goal to reach, and can be exceeded.",
                verbose_name="Goal mode",
            ),
        ),
    ]
