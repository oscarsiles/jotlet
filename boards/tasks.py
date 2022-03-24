from django.core import management

from .models import Image


def create_thumbnails(img):
    img.get_webp()
    img.get_thumbnail()
    img.get_thumbnail_webp()


def thumbnail_cleanup_command():
    return management.call_command("thumbnail", "cleanup")
