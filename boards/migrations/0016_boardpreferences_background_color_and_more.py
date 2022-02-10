# Generated by Django 4.0.2 on 2022-02-09 22:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boards', '0015_rename_photo_image_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='boardpreferences',
            name='background_color',
            field=models.CharField(blank=True, default='#ffffff', max_length=7, null=True),
        ),
        migrations.AddField(
            model_name='boardpreferences',
            name='background_opacity',
            field=models.FloatField(blank=True, default=1.0, null=True),
        ),
        migrations.AddField(
            model_name='boardpreferences',
            name='enable_latex',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='boardpreferences',
            name='require_approval',
            field=models.BooleanField(default=False),
        ),
    ]