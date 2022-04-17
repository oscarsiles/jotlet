from django.core import management


def create_thumbnails(img):
    img.get_webp()
    img.get_thumbnail()
    img.get_thumbnail_webp()


def thumbnail_cleanup_command():
    return management.call_command("thumbnail", "cleanup")


def history_clean_duplicates_past_hour_command():
    return management.call_command("clean_duplicate_history", "-m", "60", "--auto")


def history_clean_old_command():
    return management.call_command("clean_old_history", "--auto")
