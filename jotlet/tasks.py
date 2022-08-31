from django.core import management
from huey import crontab
from huey.contrib.djhuey import db_periodic_task


@db_periodic_task(crontab(hour="0"), priority=10)
def clear_sessions_command():
    return management.call_command("clearsessions")
