import os
import random
import string
import uuid
from io import BytesIO
from pathlib import Path

import auto_prefetch
from django.contrib.auth.models import User
from django.contrib.postgres.indexes import BrinIndex, GinIndex, OpClass
from django.core.files import File
from django.db import IntegrityError, models
from django.db.models.functions import Upper
from django.template.defaultfilters import date
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django_q.tasks import async_task
from mptt.models import MPTTModel, TreeForeignKey
from PIL import Image as PILImage
from simple_history.models import HistoricalRecords
from sorl.thumbnail import get_thumbnail


def get_random_string(length):
    code = "".join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(length))
    return code


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
        # Wrap the buffer in File object
        file_object = File(buffer)
        # Save the new resized file as usual, which will save to S3 using django-storages
        image.save(img_filename, file_object)


BOARD_TYPE = (
    ("d", "Default"),
    ("r", "With Replies"),
)

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

IMAGE_TYPE = (
    ("b", "Background"),
    ("p", "Post"),
)


class Board(auto_prefetch.Model):
    title = models.CharField(max_length=50)
    slug = models.SlugField(max_length=8, unique=True, null=False)
    description = models.CharField(max_length=100)
    owner = auto_prefetch.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="boards")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(cascade_delete_history=True)

    def save(self, *args, **kwargs):
        # from https://stackoverflow.com/questions/34935156/
        if self._state.adding:
            if not self.slug:
                max_length = Board._meta.get_field("slug").max_length
                self.slug = get_random_string(max_length)
                success = False
                errors = 0
                while not success:
                    try:
                        super().save(*args, **kwargs)
                    except IntegrityError:
                        errors += 1
                        if errors > 5:
                            # tried 5 times, no dice. raise the integrity error and handle elsewhere
                            raise
                        else:
                            self.code = get_random_string(max_length)
                    else:
                        success = True
            else:
                super().save(*args, **kwargs)
            BoardPreferences.objects.create(board=self)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @cached_property
    def get_posts(self):
        return Post.objects.filter(topic__board=self)

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

    @cached_property
    def get_image_count(self):
        return Image.objects.filter(board=self, type="p").count()

    get_image_count.short_description = "Image Count"

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


class BoardPreferences(auto_prefetch.Model):
    board = auto_prefetch.OneToOneField(Board, on_delete=models.CASCADE, related_name="preferences")
    history = HistoricalRecords(cascade_delete_history=True)
    type = models.CharField(max_length=1, choices=BOARD_TYPE, default="d")
    background_type = models.CharField(max_length=1, choices=BACKGROUND_TYPE, default="c")
    background_image = auto_prefetch.ForeignKey(
        "Image",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="background",
    )
    background_color = models.CharField(max_length=7, default="#ffffff")
    background_opacity = models.FloatField(default=1.0)
    enable_latex = models.BooleanField(default=False)
    require_post_approval = models.BooleanField(default=False)
    allow_guest_replies = models.BooleanField(default=False)
    allow_image_uploads = models.BooleanField(default=False)
    moderators = models.ManyToManyField(User, blank=True, related_name="moderated_boards")
    reaction_type = models.CharField(max_length=1, choices=REACTION_TYPE, default="n")

    def __str__(self):
        return self.board.title + " preferences"

    def save(self, *args, **kwargs):
        if self.background_type == "c" or (
            self.background_image.type != "b" if self.background_image is not None else True
        ):
            self.background_image = None
        super().save(*args, **kwargs)

    @cached_property
    def get_inverse_opacity(self):
        return round(1.0 - self.background_opacity, 2)

    def get_absolute_url(self):
        return reverse("boards:board-preferences", kwargs={"slug": self.board.slug})


class Topic(auto_prefetch.Model):
    subject = models.TextField(max_length=400)
    board = auto_prefetch.ForeignKey(Board, on_delete=models.CASCADE, null=True, related_name="topics")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(cascade_delete_history=True)

    def __str__(self):
        return self.subject

    def get_board_name(self):
        return self.board.title

    @cached_property
    def get_posts(self):
        return Post.objects.filter(topic=self, reply_to=None)

    @cached_property
    def get_post_count(self):
        count = 0
        for post in self.get_posts:
            count += 1
            count += post.get_descendant_count()
        return count

    get_post_count.short_description = "Post Count"

    @cached_property
    def get_last_post_date(self):
        if self.get_post_count > 0:
            return date(self.get_posts.first().created_at, "d/m/Y")
        return None

    get_last_post_date.short_description = "Last Post Date"

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"slug": self.board.slug})


class Post(auto_prefetch.Model, MPTTModel):
    content = models.TextField(max_length=1000)
    topic = auto_prefetch.ForeignKey(Topic, on_delete=models.CASCADE, null=True, related_name="posts")
    user = auto_prefetch.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="posts")
    session_key = models.CharField(max_length=40, null=True, blank=True)
    approved = models.BooleanField(default=True)
    reply_to = TreeForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    allow_replies = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class MPTTMeta:
        parent_attr = "reply_to"
        level_attr = "reply_depth"

    def __str__(self):
        return self.content

    def save(self, *args, **kwargs):
        prev_post = None
        if not self._state.adding:
            prev_post = Post.objects.get(pk=self.pk)
        super().save(*args, **kwargs)
        if prev_post is not None:
            if self.content != prev_post.content and self.topic.board.preferences.allow_image_uploads:
                async_task("boards.tasks.post_image_cleanup_task", self)

    def get_is_owner(self, request):
        return self.session_key == request.session.session_key or (
            request.user.is_authenticated and self.user == request.user
        )

    def get_reactions(self, reaction_type=None):
        if reaction_type is None:
            reaction_type = self.get_reaction_type
        return self.reactions.filter(type=reaction_type).all()

    @cached_property
    def get_reaction_type(self):
        return self.topic.board.preferences.reaction_type

    def get_reaction_score(self, reactions=None, reaction_type=None):
        try:
            if reaction_type is None:
                reaction_type = self.get_reaction_type
            if reactions is None:
                reactions = self.get_reactions(reaction_type)

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
        except Exception:
            raise Exception(f"Error calculating reaction score for: post-{self.pk}")

    def get_has_reacted(self, request, post_reactions=None):
        if post_reactions is None:
            post_reactions = self.get_reactions()

        has_reacted = False
        reaction_id = None
        reacted_score = 1  # default score

        if post_reactions:
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


class Reaction(auto_prefetch.Model):
    post = auto_prefetch.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions")
    user = auto_prefetch.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reactions")
    session_key = models.CharField(max_length=40, null=False, blank=False)
    type = models.CharField(max_length=1, choices=REACTION_TYPE, default="l")
    reaction_score = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("post", "session_key", "type"), ("post", "user", "type"))


class Image(auto_prefetch.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=50)
    attribution = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(cascade_delete_history=True)
    image = models.ImageField(upload_to=get_image_upload_path)

    type = models.CharField(max_length=1, choices=IMAGE_TYPE, default="b", help_text="Image type")
    board = auto_prefetch.ForeignKey(Board, on_delete=models.CASCADE, null=True, blank=True, related_name="images")
    post = auto_prefetch.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name="images")

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title if self.title else str(self.uuid)

    def save(self, *args, **kwargs):
        if self._state.adding:
            process_image(self.image, self.type)
        super().save(*args, **kwargs)

        if self._state.adding:
            if self.type == "b":
                async_task("boards.tasks.create_thumbnails", self)

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
