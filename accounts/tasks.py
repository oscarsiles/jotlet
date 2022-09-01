from django.core import management
from huey import crontab
from huey.contrib.djhuey import db_periodic_task


@db_periodic_task(crontab(minute="0", hour="0", day="1"), retries=3)
def axes_reset_logs():
    return management.call_command("axes_reset_logs")  # default 30 days
