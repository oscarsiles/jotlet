from django.core import management
from sorl.thumbnail import delete as sorl_delete

from .models import Image


def create_thumbnails(img):
    img.get_large_thumbnail
    img.get_large_thumbnail_webp
    img.get_small_thumbnail
    img.get_small_thumbnail_webp
    return f"created thumbnails for {img}"


def delete_thumbnails(file):
    sorl_delete(file)
    return f"deleted thumbnails for {file}"


def post_image_cleanup_task(post, imgs=None):
    if imgs is None:
        imgs = Image.objects.filter(board=post.topic.board)
    for img in imgs:
        if img.image.url in post.content and not img.post == post:
            img.post = post
            img.save()
            return "matched"
        elif img.image.url not in post.content and img.post == post:
            img.delete()
            return "deleted"
    return "no match"


def post_image_cleanup_command():
    return management.call_command("post_image_cleanup")


def thumbnail_cleanup_command():
    return management.call_command("thumbnail", "cleanup")


def history_clean_duplicates_past_hour_command():
    return management.call_command("clean_duplicate_history", "-m", "60", "--auto")


def history_clean_old_command():
    return management.call_command("clean_old_history", "--auto")
