from django.core import management


def thumbnail_cleanup_command():
    return management.call_command("thumbnail", "cleanup")
