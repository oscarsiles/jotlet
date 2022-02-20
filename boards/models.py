from io import BytesIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files import File
from django.db import models
from django.forms import UUIDField
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.html import escape
from django.utils.safestring import mark_safe
from sorl.thumbnail import get_thumbnail

from PIL import Image as PILImage

import os, uuid

from shortuuidfield import ShortUUIDField

# Create your models here.


def slug_save(obj):
    """A function to generate a 6 character numeric slug and see if it has been used."""
    if not obj.slug:  # if there isn't a slug
        obj.slug = get_random_string(6, "0123456789")  # create one
        slug_is_wrong = True
        while slug_is_wrong:  # keep checking until we have a valid slug
            slug_is_wrong = False
            other_objs_with_slug = type(obj).objects.filter(slug=obj.slug)
            if len(other_objs_with_slug) > 0:
                # if any other objects have current slug
                slug_is_wrong = True
            if slug_is_wrong:
                # create another slug and check it again
                obj.slug = get_random_string(6)


def get_image_upload_path(instance, filename):
    name, ext = os.path.splitext(filename)
    file_path = "images/{type}/{name}.{ext}".format(type=instance.type, name=instance.uuid, ext=ext.replace(".", ""))
    return file_path


def resize_image(image, width=3840, height=2160):
    # Open the image using Pillow
    img = PILImage.open(image)
    # check if either the width or height is greater than the max
    if img.width > width or img.height > height:
        output_size = (width, height)
        # Create a new resized “thumbnail” version of the image with Pillow
        img.thumbnail(output_size, PILImage.ANTIALIAS)
        # Find the file name of the image
        img_filename = Path(image.file.name).name
        # Save the resized image into the buffer, noting the correct file type
        buffer = BytesIO()
        img.save(buffer, format=img.format, quality=80, optimize=True)
        # Wrap the buffer in File object
        file_object = File(buffer)
        # Save the new resized file as usual, which will save to S3 using django-storages
        image.save(img_filename, file_object)


class Board(models.Model):
    title = models.CharField(max_length=50)
    uuid = ShortUUIDField(unique=True)
    slug = models.SlugField(max_length=6, unique=True, null=True)
    description = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="boards")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        slug_save(self)
        super(Board, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"slug": self.slug})

    class Meta:
        permissions = (("can_view_all_boards", "Can view all boards"),)


BACKGROUND_TYPE = (
    ("c", "Color"),
    ("i", "Image"),
)


class BoardPreferences(models.Model):

    board = models.OneToOneField(Board, on_delete=models.CASCADE, related_name="preferences")
    background_type = models.CharField(max_length=1, choices=BACKGROUND_TYPE, default="c")
    background_image = models.ForeignKey(
        "Image",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="background",
    )
    background_color = models.CharField(max_length=7, default="#ffffff")
    background_opacity = models.FloatField(default=1.0)
    enable_latex = models.BooleanField(default=False)
    require_approval = models.BooleanField(default=False)

    def __str__(self):
        return self.board.title + " preferences"

    def get_absolute_url(self):
        return reverse("boards:board-preferences", kwargs={"slug": self.board.slug})


class Topic(models.Model):
    subject = models.CharField(max_length=50)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, null=True, related_name="topics")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject

    def get_board_name(self):
        return self.board.title

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"slug": self.board.slug})


class Post(models.Model):
    content = models.TextField(max_length=400)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, related_name="posts")
    session_key = models.CharField(max_length=40, null=True, blank=True)
    approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.content

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"pk": self.topic.board.slug})

    class Meta:
        permissions = (("can_approve_posts", "Can approve posts"),)


class Image(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=50)
    attribution = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to=get_image_upload_path)

    IMAGE_TYPE = (("b", "Background"),)

    type = models.CharField(max_length=1, choices=IMAGE_TYPE, default="b", help_text="Image type")

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.created_at:
            resize_image(self.image)
        return super(Image, self).save(*args, **kwargs)

    def get_board_usage_count(self):
        return BoardPreferences.objects.filter(background_type="i").filter(background_image=self).count()

    get_board_usage_count.short_description = "Board Usage Count"

    def get_thumbnail_url(self):
        return get_thumbnail(self.image, "300x200", crop="center").url

    def image_tag(self):
        return mark_safe('<img src="%s" />' % escape(self.get_thumbnail_url()))

    image_tag.short_description = "Image"
    image_tag.allow_tags = True
