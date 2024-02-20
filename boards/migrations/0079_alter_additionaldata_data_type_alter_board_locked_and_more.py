# Generated by Django 5.0.2 on 2024-02-20 12:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0078_alter_additionaldata_created_at_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="additionaldata",
            name="data_type",
            field=models.CharField(
                choices=[("c", "chemdoodle"), ("f", "file"), ("m", "misc")],
                db_default="m",
                editable=False,
                max_length=1,
            ),
        ),
        migrations.AlterField(
            model_name="board",
            name="locked",
            field=models.BooleanField(db_default=False),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="allow_guest_replies",
            field=models.BooleanField(db_default=False),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="allow_image_uploads",
            field=models.BooleanField(db_default=False),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="allow_post_editing",
            field=models.BooleanField(db_default=True),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="background_color",
            field=models.CharField(db_default="#ffffff", max_length=7),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="background_opacity",
            field=models.FloatField(db_default=1.0),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="background_type",
            field=models.CharField(
                choices=[("c", "Color"), ("i", "Image")], db_default="c", max_length=1
            ),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="board_type",
            field=models.CharField(
                choices=[("d", "Default"), ("r", "With Replies")],
                db_default="d",
                max_length=1,
            ),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="enable_chemdoodle",
            field=models.BooleanField(db_default=False),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="enable_identicons",
            field=models.BooleanField(db_default=True),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="enable_latex",
            field=models.BooleanField(db_default=False),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="reaction_type",
            field=models.CharField(
                choices=[("n", "None"), ("l", "Like"), ("v", "Vote"), ("s", "Star")],
                db_default="n",
                max_length=1,
            ),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="require_post_approval",
            field=models.BooleanField(db_default=False),
        ),
        migrations.AlterField(
            model_name="boardpreferences",
            name="require_post_reapproval_on_edit",
            field=models.BooleanField(db_default=False),
        ),
        migrations.AlterField(
            model_name="export",
            name="post_count",
            field=models.PositiveSmallIntegerField(db_default=0),
        ),
        migrations.AlterField(
            model_name="image",
            name="image_type",
            field=models.CharField(
                choices=[("b", "Background"), ("p", "Post")],
                db_default="b",
                help_text="Image type",
                max_length=1,
            ),
        ),
        migrations.AlterField(
            model_name="post",
            name="allow_replies",
            field=models.BooleanField(db_default=True),
        ),
        migrations.AlterField(
            model_name="post",
            name="approved",
            field=models.BooleanField(db_default=True),
        ),
        migrations.AlterField(
            model_name="reaction",
            name="reaction_score",
            field=models.IntegerField(db_default=1),
        ),
        migrations.AlterField(
            model_name="reaction",
            name="reaction_type",
            field=models.CharField(
                choices=[("n", "None"), ("l", "Like"), ("v", "Vote"), ("s", "Star")],
                db_default="l",
                max_length=1,
            ),
        ),
        migrations.AlterField(
            model_name="topic",
            name="locked",
            field=models.BooleanField(db_default=False),
        ),
    ]
