# Generated by Django 4.0.7 on 2022-08-11 12:15

import auto_prefetch
from django.conf import settings
from django.db import migrations
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('boards', '0043_historicalpost_lft_historicalpost_reply_depth_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='boardpreferences',
            options={'base_manager_name': 'prefetch_manager'},
        ),
        migrations.AlterModelOptions(
            name='topic',
            options={'base_manager_name': 'prefetch_manager'},
        ),
        migrations.AlterModelManagers(
            name='board',
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('prefetch_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='boardpreferences',
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('prefetch_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='post',
            managers=[
                ('_tree_manager', django.db.models.manager.Manager()),
                ('prefetch_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='reaction',
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('prefetch_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='topic',
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('prefetch_manager', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterField(
            model_name='board',
            name='owner',
            field=auto_prefetch.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='boards', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='boardpreferences',
            name='background_image',
            field=auto_prefetch.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='background', to='boards.image'),
        ),
        migrations.AlterField(
            model_name='boardpreferences',
            name='board',
            field=auto_prefetch.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='preferences', to='boards.board'),
        ),
        migrations.AlterField(
            model_name='historicalboard',
            name='owner',
            field=auto_prefetch.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='historicalboardpreferences',
            name='background_image',
            field=auto_prefetch.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='boards.image'),
        ),
        migrations.AlterField(
            model_name='historicalpost',
            name='topic',
            field=auto_prefetch.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='boards.topic'),
        ),
        migrations.AlterField(
            model_name='historicalpost',
            name='user',
            field=auto_prefetch.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='historicaltopic',
            name='board',
            field=auto_prefetch.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='boards.board'),
        ),
        migrations.AlterField(
            model_name='post',
            name='topic',
            field=auto_prefetch.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='boards.topic'),
        ),
        migrations.AlterField(
            model_name='post',
            name='user',
            field=auto_prefetch.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='posts', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='reaction',
            name='post',
            field=auto_prefetch.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='boards.post'),
        ),
        migrations.AlterField(
            model_name='reaction',
            name='user',
            field=auto_prefetch.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reactions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='topic',
            name='board',
            field=auto_prefetch.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='topics', to='boards.board'),
        ),
    ]