from django.apps import apps
from django.core import management
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task, lock_task
from sorl.thumbnail import delete as sorl_delete

from jotlet.utils import offset_date


@db_task()
def create_thumbnails(img):
    # need to "get" thumbnails to create them
    _ = img.get_large_thumbnail
    _ = img.get_large_thumbnail_webp
    _ = img.get_small_thumbnail
    _ = img.get_small_thumbnail_webp
    return f"created thumbnails for {img}"


@db_task()
def delete_thumbnails(file):
    sorl_delete(file)
    return f"deleted thumbnails for {file}"


@db_periodic_task(crontab(minute="0", hour="3"))
@lock_task("export_cleanup-lock")
def export_cleanup():
    apps.get_model("boards.Export").objects.filter(created_at__lt=offset_date(days=-7)).delete()


@db_task()
@lock_task("post_image_cleanup-lock")
def post_image_cleanup(post, imgs=None):
    matched = 0
    deleted = 0
    if imgs is None:
        msg = "Post images must be provided"
        raise ValueError(msg)
    for img in imgs:
        if img.image.url in post.content and img.post != post:
            img.post = post
            img.save()
            matched += 1
        elif img.image.url not in post.content and img.post == post:
            img.delete()
            deleted += 1
    return f"{matched} matched, {deleted} deleted"


@db_periodic_task(crontab(minute="0", hour="2"))
@lock_task("post_image_cleanup-lock")
def post_image_cleanup_command():
    return management.call_command("post_image_cleanup")


@db_periodic_task(crontab(minute="0", hour="3", day_of_week="0"))
def thumbnail_cleanup_command():
    return management.call_command("thumbnail", "cleanup")
