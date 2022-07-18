from django.core import management


def clear_sessions_command():
    return management.call_command("clearsessions")


def clear_conj_keys_command():
    return management.call_command("reapconjs")
