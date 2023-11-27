import csv
import datetime
import secrets
import string
import sys
from io import BytesIO, StringIO
from pathlib import Path
from uuid import uuid4

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image as PILImage


def channel_group_send(group_name, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name, message)


def get_export_upload_path(export, filename):
    timestamp = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d-%H%M%S")
    ext = Path(filename).suffix
    return f"exports/boards/{get_random_string(2)}/{uuid4()}/{export.board.slug}_{timestamp}{ext}"


def generate_csv(header, rows):
    with StringIO(newline="") as csv_buffer:
        csv_writer = csv.DictWriter(csv_buffer, fieldnames=header)
        csv_writer.writeheader()
        csv_writer.writerows(iter(rows))

        bytes_buffer = BytesIO(csv_buffer.getvalue().encode("utf-8"))

    return InMemoryUploadedFile(
        bytes_buffer,
        "FileField",
        "export.csv",
        "text/csv",
        sys.getsizeof(bytes_buffer),
        "utf-8",
    )


def get_image_upload_path(image, filename):
    ext = Path(filename).suffix
    sub1 = image.board.slug if image.image_type == "p" else get_random_string(2)
    sub2 = get_random_string(2)
    return f"images/{image.image_type}/{sub1}/{sub2}/{image.id}{ext}"


def get_is_moderator(user, board):
    return (
        user.has_perm("boards.can_approve_posts")
        or user in board.preferences.moderators.all()
        or user == board.owner
        or user.is_staff
    )


def get_random_string(length):
    return "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(length))


def post_reaction_send_update_message(post):
    channel_group_send(
        f"board-{post.topic.board.slug}",
        {
            "type": "reaction_updated",
            "topic_pk": str(post.topic.pk),
            "post_pk": str(post.pk),
        },
    )


def open_image(image):
    return PILImage.open(image)


def convert_image_format(img, image):
    output_format = img.format
    converted = False
    if img.format not in ["JPEG", "PNG"]:
        output_format = "JPEG"
        name = Path(image.name).stem
        image.name = f"{name}.jpg"
        if img.mode != "RGB":
            img = img.convert("RGB")
        converted = True
    return img, output_format, converted


def resize_image(img, width, height):
    if img.width > width or img.height > height:
        output_size = (width, height)
        img.thumbnail(output_size, PILImage.Resampling.LANCZOS)
        return img, True
    return img, False


def save_image(img, image, output_format):
    buffer = BytesIO()
    img.save(buffer, format=output_format, quality=80, optimize=True)
    return InMemoryUploadedFile(buffer, "ImageField", image.name, output_format, sys.getsizeof(buffer), None)


def process_image(image, image_type="b", width=settings.MAX_IMAGE_WIDTH, height=settings.MAX_IMAGE_HEIGHT):
    if image_type == "p":
        width = settings.MAX_POST_IMAGE_WIDTH
        height = settings.MAX_POST_IMAGE_HEIGHT

    img = open_image(image)
    img, output_format, format_changed = convert_image_format(img, image)
    img, size_changed = resize_image(img, width, height)

    if format_changed or size_changed:
        image = save_image(img, image, output_format)

    return image
