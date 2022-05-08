from django.core import management


def axes_reset_logs():
    return management.call_command("axes_reset_logs")  # default 30 days
