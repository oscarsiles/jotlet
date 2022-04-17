import os
import uuid
from io import BytesIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files import File
from django.db import models
from django.db.models import Sum
from django.template.defaultfilters import date
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from django.utils.html import escape
from django.utils.safestring import mark_safe
from PIL import Image as PILImage
from shortuuidfield import ShortUUIDField
from simple_history.models import HistoricalRecords
from sorl.thumbnail import get_thumbnail


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
    history = HistoricalRecords(cascade_delete_history=True)

    def save(self, *args, **kwargs):
        slug_save(self)
        super(Board, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    @cached_property
    def get_posts(self):
        return Post.objects.filter(topic__board=self).order_by("-created_at")

    @cached_property
    def get_post_count(self):
        return self.get_posts.count()

    get_post_count.short_description = "Post Count"

    @cached_property
    def get_last_post_date(self):
        if self.get_post_count > 0:
            return date(self.get_posts.first().created_at, "d/m/Y")
        return None

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"slug": self.slug})

    class Meta:
        permissions = (("can_view_all_boards", "Can view all boards"),)


BACKGROUND_TYPE = (
    ("c", "Color"),
    ("i", "Image"),
)

REACTION_TYPE = (
    ("n", "None"),
    ("l", "Like"),  # 1 = like
    ("v", "Vote"),  # 1 = like, -1 = dislike
    ("s", "Star"),  # 1-5 = stars
)


class BoardPreferences(models.Model):
    board = models.OneToOneField(Board, on_delete=models.CASCADE, related_name="preferences")
    history = HistoricalRecords(cascade_delete_history=True)
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
    moderators = models.ManyToManyField(User, blank=True, related_name="moderated_boards")
    reaction_type = models.CharField(max_length=1, choices=REACTION_TYPE, default="n")

    def __str__(self):
        return self.board.title + " preferences"

    def save(self, *args, **kwargs):
        if self.background_type == "c" or (
            self.background_image.type != "b" if self.background_image is not None else True
        ):
            self.background_image = None
        super(BoardPreferences, self).save(*args, **kwargs)

    @cached_property
    def get_inverse_opacity(self):
        return round(1.0 - self.background_opacity, 2)

    def get_absolute_url(self):
        return reverse("boards:board-preferences", kwargs={"slug": self.board.slug})


class Topic(models.Model):
    subject = models.CharField(max_length=50)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, null=True, related_name="topics")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(cascade_delete_history=True)

    def __str__(self):
        return self.subject

    def get_board_name(self):
        return self.board.title

    @cached_property
    def get_posts(self):
        return Post.objects.filter(topic=self).order_by("-created_at")

    @cached_property
    def get_post_count(self):
        return self.get_posts.count()

    get_post_count.short_description = "Post Count"

    @cached_property
    def get_last_post_date(self):
        if self.get_post_count > 0:
            return date(self.get_posts.first().created_at, "d/m/Y")
        return None

    get_last_post_date.short_description = "Last Post Date"

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"slug": self.board.slug})


class Post(models.Model):
    content = models.TextField(max_length=400)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, related_name="posts")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="posts")
    session_key = models.CharField(max_length=40, null=True, blank=True)
    approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(cascade_delete_history=True)

    def __str__(self):
        return self.content

    @cached_property
    def get_reaction_score(self):
        reaction_type = self.topic.board.preferences.reaction_type
        # cannot use match/switch before python 3.10
        if reaction_type == "n":
            return 0
        elif reaction_type == "l":
            return Reaction.objects.filter(post=self, type="l").count()
        elif reaction_type == "v":
            all_reactions = Reaction.objects.filter(post=self, type="v")
            return all_reactions.filter(reaction_score=1).count(), all_reactions.filter(reaction_score=-1).count()
        elif reaction_type == "s":
            score = ""
            try:
                reactions = Reaction.objects.filter(post=self, type="s")
                sum = reactions.aggregate(Sum("reaction_score"))["reaction_score__sum"]
                count = reactions.count()
                score = f"{(sum / count):.2g}"
            except:
                pass
            return score

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"slug": self.topic.board.slug})

    class Meta:
        permissions = (("can_approve_posts", "Can approve posts"),)


class Reaction(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reactions")
    session_key = models.CharField(max_length=40, null=False, blank=False)
    type = models.CharField(max_length=1, choices=REACTION_TYPE, default="l")
    reaction_score = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("post", "session_key", "type"), ("post", "user", "type"))


IMAGE_TYPE = (("b", "Background"), ("p", "Post"))


class Image(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=50)
    attribution = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(cascade_delete_history=True)
    image = models.ImageField(upload_to=get_image_upload_path)

    type = models.CharField(max_length=1, choices=IMAGE_TYPE, default="b", help_text="Image type")

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.created_at:
            resize_image(self.image)
        return super(Image, self).save(*args, **kwargs)

    @cached_property
    def get_board_usage_count(self):
        return BoardPreferences.objects.filter(background_type="i").filter(background_image=self).count()

    get_board_usage_count.short_description = "Board Usage Count"

    @cached_property
    def get_image_dimensions(self):
        return f"{self.image.width}x{self.image.height}"

    def get_webp(self):
        return get_thumbnail(self.image, self.get_image_dimensions, quality=70, format="WEBP")

    def get_thumbnail(self):
        return get_thumbnail(self.image, "300x200", crop="center", quality=80, format="JPEG")

    def get_thumbnail_webp(self):
        return get_thumbnail(self.image, "300x200", crop="center", quality=80, format="WEBP")

    def image_tag(self):
        return mark_safe(f'<img src="{escape(self.get_thumbnail().url)}" />')

    image_tag.short_description = "Image"
    image_tag.allow_tags = True
