# Generated by Django 4.2.1 on 2023-05-09 21:59

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0064_boardpreferences_uuid_post_uuid_reaction_uuid_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="boardpreferences",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
        migrations.AlterField(
            model_name="post",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
        migrations.AlterField(
            model_name="reaction",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
        migrations.AlterField(
            model_name="topic",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]
