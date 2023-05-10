# Generated by Django 4.2.1 on 2023-05-10 18:30

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("boards", "0069_historicaltopic_historicalpost_historicalimage_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="boardpreferences",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="historicalboardpreferences",
            name="updated_at",
            field=models.DateTimeField(
                blank=True,
                default=datetime.datetime(2023, 5, 10, 18, 30, 37, 594833, tzinfo=datetime.timezone.utc),
                editable=False,
            ),
            preserve_default=False,
        ),
    ]
