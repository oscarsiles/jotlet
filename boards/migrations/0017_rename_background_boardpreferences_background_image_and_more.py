# Generated by Django 4.0.2 on 2022-02-10 17:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boards', '0016_boardpreferences_background_color_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='boardpreferences',
            old_name='background',
            new_name='background_image',
        ),
        migrations.AddField(
            model_name='boardpreferences',
            name='background_type',
            field=models.CharField(choices=[('c', 'Color'), ('i', 'Image')], default='c', max_length=1),
        ),
    ]
