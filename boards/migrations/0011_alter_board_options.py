# Generated by Django 4.0.2 on 2022-02-02 14:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('boards', '0010_board_slug'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='board',
            options={'permissions': (('can_view_all_boards', 'Can view all boards'),)},
        ),
    ]
