# Generated by Django 4.0.2 on 2022-02-02 10:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('boards', '0007_board_owner'),
    ]

    operations = [
        migrations.AlterField(
            model_name='board',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='boards', to=settings.AUTH_USER_MODEL),
        ),
    ]
