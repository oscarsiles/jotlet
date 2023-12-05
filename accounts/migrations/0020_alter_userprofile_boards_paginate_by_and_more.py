# Generated by Django 5.0 on 2023-12-05 14:52

import django.contrib.postgres.functions
import django.db.models.functions.datetime
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0019_delete_historicaluserprofile"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="boards_paginate_by",
            field=models.PositiveSmallIntegerField(db_default=models.Value(10)),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="created_at",
            field=models.DateTimeField(
                db_default=django.db.models.functions.datetime.Now(), editable=False
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="id",
            field=models.UUIDField(
                db_default=django.contrib.postgres.functions.RandomUUID(),
                default=uuid.uuid4,
                editable=False,
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="optin_newsletter",
            field=models.BooleanField(
                db_default=models.Value(False), verbose_name="Opt-in to newsletter"
            ),
        ),
    ]
