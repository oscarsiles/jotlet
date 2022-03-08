from django.core import management

from .models import Image


def create_thumbnail(img):
    return img.get_thumbnail()


def thumbnail_cleanup_command():
    return management.call_command("thumbnail", "cleanup")
