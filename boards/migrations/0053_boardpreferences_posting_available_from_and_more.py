# Generated by Django 4.1.1 on 2022-09-16 14:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("boards", "0052_alter_board_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="boardpreferences",
            name="posting_allowed_from",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="boardpreferences",
            name="posting_allowed_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicalboardpreferences",
            name="posting_allowed_from",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicalboardpreferences",
            name="posting_allowed_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
