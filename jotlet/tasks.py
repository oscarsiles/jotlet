from django.core import management


def clear_sessions_command():
    return management.call_command("clearsessions")
