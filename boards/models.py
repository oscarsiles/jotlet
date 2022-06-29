import os
import uuid
from io import BytesIO
from pathlib import Path

from django.contrib.auth.models import User
from django.contrib.postgres.indexes import BrinIndex, GinIndex, OpClass
from django.core.files import File
from django.db import models
from django.db.models.functions import Upper
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
    _, ext = os.path.splitext(filename)
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
        if self._state.adding:
            slug_save(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @cached_property
    def get_posts(self):
        return Post.objects.filter(topic__board=self).prefetch_related("reactions").order_by("-created_at")

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
        indexes = [
            GinIndex(
                OpClass(Upper("title"), name="gin_trgm_ops"),
                name="upper_title_idx",
            ),
            GinIndex(
                OpClass(Upper("description"), name="gin_trgm_ops"),
                name="upper_description_idx",
            ),
            BrinIndex(fields=["created_at"], autosummarize=True),
        ]


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
    subject = models.TextField(max_length=400)
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
        return Post.objects.filter(topic=self).prefetch_related("reactions").order_by("-created_at")

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
    def get_reactions(self):
        return self.reactions.filter(type=self.topic.board.preferences.reaction_type).all()

    @cached_property
    def get_reaction_type(self):
        return self.topic.board.preferences.reaction_type

    @cached_property
    def get_reaction_count(self):
        return len(self.get_reactions)

    def get_is_owner(self, request):
        return self.user == request.user or self.session_key == request.session.session_key

    @cached_property
    def get_reaction_score(self):
        try:
            reaction_type = self.get_reaction_type
            if reaction_type == "n":
                return 0

            reactions = self.get_reactions

            if reaction_type == "l":  # cannot use match/switch before python 3.10
                return reactions.count()
            elif reaction_type == "v":
                return sum(1 for reaction in reactions if reaction.reaction_score == 1), sum(
                    1 for reaction in reactions if reaction.reaction_score == -1
                )
            elif reaction_type == "s":
                score = ""
                count = reactions.count()
                if count != 0:
                    sumvar = sum(reaction.reaction_score for reaction in reactions)
                    score = f"{(sumvar / count):.2g}"
                return score
            else:
                return 0
        except:
            raise Exception(f"Error calculating reaction score for: post-{self.pk}")

    def get_has_reacted(self, request):
        post_reactions = self.get_reactions
        has_reacted = False
        reaction_id = None
        reacted_score = 1  # default score

        if post_reactions.count() > 0:
            if request.session.session_key:
                for reaction in post_reactions:
                    if reaction.session_key == request.session.session_key:
                        has_reacted = True
                        reaction_id = reaction.id
                        reacted_score = reaction.reaction_score
                        break

            if request.user.is_authenticated and not has_reacted:
                for reaction in post_reactions:
                    if reaction.user == request.user:
                        has_reacted = True
                        reaction_id = reaction.id
                        reacted_score = reaction.reaction_score
                        break

        return has_reacted, reaction_id, reacted_score

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
        return super().save(*args, **kwargs)

    @cached_property
    def get_board_usage_count(self):
        return BoardPreferences.objects.filter(background_type="i").filter(background_image=self).count()

    get_board_usage_count.short_description = "Board Usage Count"

    @cached_property
    def get_image_dimensions(self):
        return f"{self.image.width}x{self.image.height}"

    @cached_property
    def get_webp(self):
        return get_thumbnail(self.image, self.get_image_dimensions, quality=70, format="WEBP")

    @cached_property
    def get_thumbnail(self):
        return get_thumbnail(self.image, "300x200", crop="center", quality=80, format="JPEG")

    @cached_property
    def get_thumbnail_webp(self):
        return get_thumbnail(self.image, "300x200", crop="center", quality=80, format="WEBP")

    @cached_property
    def image_tag(self):
        return mark_safe(f'<img src="{escape(self.get_thumbnail.url)}" />')

    image_tag.short_description = "Image"
    image_tag.allow_tags = True
