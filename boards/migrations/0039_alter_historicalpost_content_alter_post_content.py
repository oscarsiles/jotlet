# Generated by Django 4.0.6 on 2022-07-08 15:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boards', '0038_remove_board_uuid_remove_historicalboard_uuid_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalpost',
            name='content',
            field=models.TextField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='post',
            name='content',
            field=models.TextField(max_length=1000),
        ),
    ]
