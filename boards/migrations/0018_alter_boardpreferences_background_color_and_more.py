# Generated by Django 4.0.2 on 2022-02-11 00:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boards', '0017_rename_background_boardpreferences_background_image_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='boardpreferences',
            name='background_color',
            field=models.CharField(default='#ffffff', max_length=7),
        ),
        migrations.AlterField(
            model_name='boardpreferences',
            name='background_opacity',
            field=models.FloatField(default=1.0),
        ),
    ]