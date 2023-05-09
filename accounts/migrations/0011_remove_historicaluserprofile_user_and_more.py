import uuid

from django.db import migrations, models


def gen_uuid(apps, schema_editor):
    Model = apps.get_model("accounts", "historicaluserprofile")
    for row in Model.objects.all():
        old_id = row.history_id
        while True:
            row.history_id = uuid.uuid4()
            if not Model.objects.filter(history_id=row.history_id).exists():
                break
        row.save()
        Model.objects.get(history_id=old_id).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_alter_userprofile_options"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="historicaluserprofile",
            name="user",
        ),
        migrations.AlterField(
            model_name="historicaluserprofile",
            name="history_id",
            field=models.CharField(
                auto_created=True, editable=False, max_length=36, primary_key=True, serialize=False
            ),
        ),
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
    ]
