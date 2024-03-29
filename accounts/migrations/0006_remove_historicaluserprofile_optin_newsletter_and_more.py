# Generated by Django 4.1.2 on 2022-10-22 22:03

from django.db import migrations, models


def migrate_optin_newsletter(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.all():
        user.optin_newsletter = user.profile.optin_newsletter
        user.save(update_fields=["optin_newsletter"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_alter_historicaluserprofile_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="optin_newsletter",
            field=models.BooleanField(default=False, verbose_name="Opt-in to newsletter"),
        ),
        migrations.RunPython(migrate_optin_newsletter, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="historicaluserprofile",
            name="optin_newsletter",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="optin_newsletter",
        ),
    ]
