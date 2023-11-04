import os
import random
import string
import sys
from io import BytesIO

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image as PILImage


def channel_group_send(group_name, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name, message)


def get_image_upload_path(image, filename):
    _, ext = os.path.splitext(filename)
    return "images/{image_type}/{sub1}/{sub2}/{name}.{ext}".format(
        image_type=image.image_type,
        sub1=image.board.slug
        if image.image_type == "p"
        else get_random_string(2),
        sub2=get_random_string(2),
        name=image.id,
        ext=ext.replace(".", ""),
    )


def get_is_moderator(user, board):
    return (
        user.has_perm("boards.can_approve_posts")
        or user in board.preferences.moderators.all()
        or user == board.owner
        or user.is_staff
    )


def get_random_string(length):
    return "".join(
        random.SystemRandom().choice(string.ascii_lowercase + string.digits)
        for _ in range(length)
    )


def post_reaction_send_update_message(post):
    try:
        channel_group_send(
            f"board-{post.topic.board.slug}",
            {
                "type": "reaction_updated",
                "topic_pk": str(post.topic.pk),
                "post_pk": str(post.pk),
            },
        )
    except Exception:
        raise Exception(f"Could not send message: reaction_updated for reaction-{post.pk}")


def process_image(image, image_type="b", width=settings.MAX_IMAGE_WIDTH, height=settings.MAX_IMAGE_HEIGHT):
    process = False
    # Open the image using Pillow
    img = PILImage.open(image)
    if image_type == "p":
        width = settings.MAX_POST_IMAGE_WIDTH
        height = settings.MAX_POST_IMAGE_HEIGHT

    if img.format not in ["JPEG", "PNG"]:
        output_format = "JPEG"
        name, _ = os.path.splitext(image.name)
        image.name = f"{name}.jpg"
        if img.mode != "RGB":
            img = img.convert("RGB")
        process = True
    else:
        output_format = img.format

    if img.width > width or img.height > height:
        process = True
    else:
        width = img.width
        height = img.height

    if process:
        # Adapted from https://blog.soards.me/posts/resize-image-on-save-in-django-before-sending-to-amazon-s3/
        output_size = (width, height)
        # Create a new resized “thumbnail” version of the image with Pillow
        img.thumbnail(output_size, PILImage.Resampling.LANCZOS)
        # Find the file name of the image
        img_filename = os.path.basename(image.name)
        # Save the resized image into the buffer, noting the correct file type
        buffer = BytesIO()
        img.save(buffer, format=output_format, quality=80, optimize=True)
        # Save the new resized file
        image = InMemoryUploadedFile(buffer, "ImageField", img_filename, output_format, sys.getsizeof(buffer), None)
    return image
