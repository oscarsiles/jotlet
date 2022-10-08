from django.core import management
from huey import crontab
from huey.contrib.djhuey import db_periodic_task


@db_periodic_task(crontab(minute="5", hour="0"), retries=3)
def axes_reset_logs():
    return management.call_command("axes_reset_logs", "--age", "30")  # default 30 days
