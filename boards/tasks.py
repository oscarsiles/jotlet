from django.core import management
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task, lock_task
from sorl.thumbnail import delete as sorl_delete


@db_task()
def create_thumbnails(img):
    img.get_large_thumbnail
    img.get_large_thumbnail_webp
    img.get_small_thumbnail
    img.get_small_thumbnail_webp
    return f"created thumbnails for {img}"


@db_task()
def delete_thumbnails(file):
    sorl_delete(file)
    return f"deleted thumbnails for {file}"


@db_task()
@lock_task("post_image_cleanup-lock")
def post_image_cleanup(post, imgs=None):
    if imgs is None:
        raise ValueError("Post images must be provided")
    for img in imgs:
        if img.image.url in post.content and not img.post == post:
            img.post = post
            img.save()
            return "matched"
        elif img.image.url not in post.content and img.post == post:
            img.delete()
            return "deleted"
    return "no match"


@db_periodic_task(crontab(minute="30"))
def history_clean_duplicates_past_hour_command():
    return management.call_command("clean_duplicate_history", "-m", "60", "--auto")


@db_periodic_task(crontab(minute="0", hour="1"))
def history_clean_old_command():
    return management.call_command("clean_old_history", "--auto")


@db_periodic_task(crontab(minute="0", hour="2"))
@lock_task("post_image_cleanup-lock")
def post_image_cleanup_command():
    return management.call_command("post_image_cleanup")


@db_periodic_task(crontab(minute="0", hour="3", day_of_week="0"))
def thumbnail_cleanup_command():
    return management.call_command("thumbnail", "cleanup")
