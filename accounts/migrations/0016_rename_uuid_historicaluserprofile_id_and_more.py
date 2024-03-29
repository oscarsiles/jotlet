# Generated by Django 4.2.1 on 2023-05-09 23:02


import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0015_remove_historicaluserprofile_id_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="userprofile",
            old_name="uuid",
            new_name="id",
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.DeleteModel(
            name="HistoricalUserProfile",
        ),
    ]
