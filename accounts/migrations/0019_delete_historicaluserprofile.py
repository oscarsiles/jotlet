# Generated by Django 4.2.6 on 2023-10-06 21:20

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0018_userprofile_accounts_us_created_c69f42_brin"),
    ]

    operations = [
        migrations.DeleteModel(
            name="HistoricalUserProfile",
        ),
    ]
