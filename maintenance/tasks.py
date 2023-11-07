from django.core import management
from huey import crontab
from huey.contrib.djhuey import db_periodic_task
from huey_monitor.models import SignalInfoModel, TaskModel

from jotlet.utils import offset_date


@db_periodic_task(crontab(minute="0", hour="0"), retries=2)
def clear_sessions_command():
    return management.call_command("clearsessions")


@db_periodic_task(crontab(minute="30", hour="0"), retries=2)
def clear_old_tasks():
    delete_older_than = offset_date(7)
    SignalInfoModel.objects.filter(create_dt__lte=delete_older_than).delete()
    TaskModel.objects.filter(create_dt__lte=delete_older_than).delete()
