# Generated by Django 4.0.2 on 2022-02-02 14:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boards', '0009_alter_post_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='board',
            name='slug',
            field=models.SlugField(max_length=6, null=True, unique=True),
        ),
    ]