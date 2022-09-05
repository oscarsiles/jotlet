import datetime

from django.core import management
from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task
from huey_monitor.models import SignalInfoModel, TaskModel


@db_periodic_task(crontab(minute="0", hour="0"), retries=2)
def clear_sessions_command():
    return management.call_command("clearsessions")


@db_periodic_task(crontab(minute="30", hour="0"), retries=2)
def clear_old_tasks():
    delete_older_than = timezone.now() - datetime.timedelta(days=7)
    SignalInfoModel.objects.filter(create_dt__lte=delete_older_than).delete()
    TaskModel.objects.filter(create_dt__lte=delete_older_than).delete()
