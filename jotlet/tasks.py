from django.core import management
from huey import crontab
from huey.contrib.djhuey import db_periodic_task


@db_periodic_task(crontab(minute="0", hour="0"), retries=2)
def clear_sessions_command():
    return management.call_command("clearsessions")
