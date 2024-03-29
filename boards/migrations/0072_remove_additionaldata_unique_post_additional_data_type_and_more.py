# Generated by Django 4.2.1 on 2023-05-22 15:04

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0071_alter_board_options_alter_image_options_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="additionaldata",
            name="unique_post_additional_data_type",
        ),
        migrations.RemoveConstraint(
            model_name="reaction",
            name="unique_anonymous_reaction",
        ),
        migrations.RemoveConstraint(
            model_name="reaction",
            name="unique_user_reaction",
        ),
        migrations.RenameField(
            model_name="additionaldata",
            old_name="type",
            new_name="data_type",
        ),
        migrations.RenameField(
            model_name="boardpreferences",
            old_name="type",
            new_name="board_type",
        ),
        migrations.RenameField(
            model_name="historicalboardpreferences",
            old_name="type",
            new_name="board_type",
        ),
        migrations.RenameField(
            model_name="image",
            old_name="type",
            new_name="image_type",
        ),
        migrations.RenameField(
            model_name="reaction",
            old_name="type",
            new_name="reaction_type",
        ),
        migrations.AddConstraint(
            model_name="additionaldata",
            constraint=models.UniqueConstraint(fields=("post", "data_type"), name="unique_post_additional_data_type"),
        ),
        migrations.AddConstraint(
            model_name="reaction",
            constraint=models.UniqueConstraint(
                fields=("post", "session_key", "reaction_type"), name="unique_anonymous_reaction"
            ),
        ),
        migrations.AddConstraint(
            model_name="reaction",
            constraint=models.UniqueConstraint(fields=("post", "user", "reaction_type"), name="unique_user_reaction"),
        ),
    ]
