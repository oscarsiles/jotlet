# Generated by Django 4.0.1 on 2022-01-31 11:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boards', '0003_alter_post_topic_alter_topic_board'),
    ]

    operations = [
        migrations.AddField(
            model_name='board',
            name='uuid',
            field=models.UUIDField(blank=True, editable=False, max_length=22, unique=True),
        ),
    ]
