import os
import random
import string
import sys
from io import BytesIO
from pathlib import Path

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image as PILImage


def channel_group_send(group_name, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name, message)


def get_image_upload_path(instance, filename):
    _, ext = os.path.splitext(filename)
    file_path = "images/{type}/{sub1}/{sub2}/{name}.{ext}".format(
        type=instance.type,
        sub1=instance.board.slug if instance.type == "p" else get_random_string(2),
        sub2=get_random_string(2),
        name=instance.uuid,
        ext=ext.replace(".", ""),
    )
    return file_path


def get_random_string(length):
    code = "".join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(length))
    return code


def process_image(image, type="b", width=3840, height=2160):
    process = False
    # Open the image using Pillow
    img = PILImage.open(image)
    if type == "p":
        width = 400
        height = 400

    if img.format not in ["JPEG", "PNG"]:
        output_format = "JPEG"
        name, _ = os.path.splitext(image.file.name)
        image.file.name = name + ".jpg"
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
        img_filename = Path(image.file.name).name
        # Save the resized image into the buffer, noting the correct file type
        buffer = BytesIO()
        img.save(buffer, format=output_format, quality=80, optimize=True)
        # Save the new resized file
        image = InMemoryUploadedFile(buffer, "ImageField", img_filename, output_format, sys.getsizeof(buffer), None)
    return image
