import uuid
from hashlib import blake2b

import auto_prefetch
from cacheops import cached_as
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.indexes import BrinIndex, GinIndex, OpClass
from django.db import IntegrityError, models
from django.db.models.functions import Upper
from django.template.defaultfilters import date
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import escape
from django.utils.safestring import mark_safe
from simple_history.models import HistoricalRecords
from sorl.thumbnail import get_thumbnail
from tree_queries.models import TreeNode
from tree_queries.query import TreeQuerySet

from .tasks import create_thumbnails, post_image_cleanup
from .utils import get_image_upload_path, get_random_string, process_image

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
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=False, unique=True)  # used as salt for hashing
    owner = auto_prefetch.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="boards")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(cascade_delete_history=True)

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
    def get_postimage_count(self):
        return Image.objects.filter(board=self, type="p").count()

    get_postimage_count.short_description = "Image Count"

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"slug": self.slug})

    @cached_property
    def is_posting_allowed(self):
        is_allowed = True
        if self.preferences.posting_allowed_from is not None and self.preferences.posting_allowed_until is not None:
            if self.preferences.posting_allowed_from <= self.preferences.posting_allowed_until:
                is_allowed = (
                    self.preferences.posting_allowed_from <= timezone.now() <= self.preferences.posting_allowed_until
                )
            else:  # disallowed period falls between from/until dates
                is_allowed = (
                    timezone.now() >= self.preferences.posting_allowed_from
                    or timezone.now() <= self.preferences.posting_allowed_until
                )
        elif self.preferences.posting_allowed_from is not None:
            is_allowed = self.preferences.posting_allowed_from <= timezone.now()
        elif self.preferences.posting_allowed_until is not None:
            is_allowed = timezone.now() <= self.preferences.posting_allowed_until
        return is_allowed


class BoardPreferences(auto_prefetch.Model):
    board = auto_prefetch.OneToOneField(Board, on_delete=models.CASCADE, related_name="preferences")
    history = HistoricalRecords(cascade_delete_history=True)
    type = models.CharField(max_length=1, choices=BOARD_TYPE, default="d")
    background_type = models.CharField(max_length=1, choices=BACKGROUND_TYPE, default="c")
    background_image = auto_prefetch.ForeignKey(
        "BgImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="background",
    )
    background_color = models.CharField(max_length=7, default="#ffffff")
    background_opacity = models.FloatField(default=1.0)
    enable_latex = models.BooleanField(default=False)
    enable_identicons = models.BooleanField(default=True)
    require_post_approval = models.BooleanField(default=False)
    allow_guest_replies = models.BooleanField(default=False)
    allow_image_uploads = models.BooleanField(default=False)
    moderators = models.ManyToManyField(User, blank=True, related_name="moderated_boards")
    reaction_type = models.CharField(max_length=1, choices=REACTION_TYPE, default="n")
    posting_allowed_from = models.DateTimeField(null=True, blank=True)
    posting_allowed_until = models.DateTimeField(null=True, blank=True)

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
        return Post.objects.filter(topic=self, parent=None)

    @cached_property
    def get_post_count(self):
        @cached_as(self, timeout=60 * 60 * 24)
        def _get_post_count():
            count = 0
            for post in self.get_posts:
                count += 1
                count += post.descendants().count()
            return count

        return _get_post_count()

    get_post_count.short_description = "Post Count"

    @cached_property
    def get_last_post_date(self):
        if self.get_post_count > 0:
            return date(self.get_posts.first().created_at, "d/m/Y")
        return None

    get_last_post_date.short_description = "Last Post Date"

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"slug": self.board.slug})


class Post(auto_prefetch.Model, TreeNode):
    objects = TreeQuerySet.as_manager(with_tree_fields=True)
    content = models.TextField(max_length=1000)
    topic = auto_prefetch.ForeignKey(Topic, on_delete=models.CASCADE, null=True, related_name="posts")
    user = auto_prefetch.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="posts")
    session_key = models.CharField(max_length=40, null=True, blank=True)
    identity_hash = models.CharField(max_length=64, null=True, blank=True)
    approved = models.BooleanField(default=True)
    allow_replies = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = (("can_approve_posts", "Can approve posts"),)

    def __str__(self):
        return self.content

    def save(self, *args, **kwargs):
        prev_post = None
        if not self._state.adding:
            prev_post = Post.objects.get(pk=self.pk)
        else:
            string = self.user.username if self.user is not None else self.session_key
            salt = self.topic.board.uuid
            self.identity_hash = blake2b(f"{string}{salt}".encode(), digest_size=32).hexdigest()
        super().save(*args, **kwargs)

        if self.topic.board.preferences.allow_image_uploads:
            cleanup_task = False
            if prev_post is None:
                cleanup_task = True
            elif prev_post.content != self.content:
                cleanup_task = True
            if cleanup_task:
                post_image_cleanup(self, PostImage.objects.filter(board=self.topic.board))()

    def get_is_owner(self, request):
        return (self.session_key == request.session.session_key and self.session_key is not None) or (
            request.user.is_authenticated and self.user == request.user
        )

    def get_reactions(self, reaction_type=None):
        @cached_as(self, extra=reaction_type, timeout=60 * 60 * 24)
        def _get_reactions(reaction_type):
            if reaction_type is None:
                reaction_type = self.get_reaction_type
            return Reaction.objects.filter(post=self, type=reaction_type)

        return _get_reactions(reaction_type)

    @cached_property
    def get_reaction_type(self):
        return self.topic.board.preferences.reaction_type

    def get_reaction_score(self, reactions=None, reaction_type=None):
        if reaction_type is None:
            reaction_type = self.get_reaction_type
        if reactions is None:
            reactions = self.get_reactions(reaction_type)

        @cached_as(reactions, extra=reaction_type, timeout=60 * 60 * 24)
        def _get_reaction_score(reactions, reaction_type):
            try:
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

        return _get_reaction_score(reactions, reaction_type)

    def get_has_reacted(self, request, post_reactions=None):
        if post_reactions is None:
            post_reactions = self.get_reactions()

        has_reacted = False
        reaction_id = None
        reacted_score = 1  # default score

        @cached_as(post_reactions, extra=request.session.session_key, timeout=60 * 60 * 24)
        def _get_has_reacted_session_key():
            for reaction in post_reactions:
                if reaction.session_key == request.session.session_key:
                    return True, reaction.pk, reaction.reaction_score
            return False, None, 1

        @cached_as(post_reactions, extra=request.user, timeout=60 * 60 * 24)
        def _get_has_reacted_user():
            for reaction in post_reactions:
                if reaction.user == request.user:
                    return True, reaction.pk, reaction.reaction_score
            return False, None, 1

        if post_reactions:
            if request.session.session_key:
                has_reacted, reaction_id, reacted_score = _get_has_reacted_session_key()

            if request.user.is_authenticated and not has_reacted:
                has_reacted, reaction_id, reacted_score = _get_has_reacted_user()

        return has_reacted, reaction_id, reacted_score

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"slug": self.topic.board.slug})


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
        created = self._state.adding
        if created:
            self.image = process_image(self.image, self.type)
        super().save(*args, **kwargs)

        if created:
            if self.type == "b":
                create_thumbnails(self)()

    @cached_property
    def get_board_usage_count(self):
        return BoardPreferences.objects.filter(background_type="i", background_image=self).count()

    get_board_usage_count.short_description = "Board Usage Count"

    @cached_property
    def get_image_dimensions(self):
        return f"{self.image.width}x{self.image.height}"

    @cached_property
    def get_half_image_dimensions(self):
        return f"{self.image.width // 2}x{self.image.height // 2}"

    @cached_property
    def get_small_thumbnail_dimensions(self):
        return f"{settings.SMALL_THUMBNAIL_WIDTH}x{settings.SMALL_THUMBNAIL_HEIGHT}"

    @cached_property
    def get_webp(self):
        @cached_as(self)
        def _get_webp():
            return get_thumbnail(self.image, self.get_image_dimensions, quality=70, format="WEBP")

        return _get_webp()

    @cached_property
    def get_large_thumbnail(self):
        @cached_as(self)
        def _get_large_thumbnail():
            return get_thumbnail(self.image, self.get_half_image_dimensions, quality=70, format="JPEG")

        return _get_large_thumbnail()

    @cached_property
    def get_large_thumbnail_webp(self):
        @cached_as(self)
        def _get_large_thumbnail_webp():
            return get_thumbnail(self.image, self.get_half_image_dimensions, quality=70, format="WEBP")

        return _get_large_thumbnail_webp()

    @cached_property
    def get_small_thumbnail(self):
        @cached_as(self)
        def _get_small_thumbnail():
            return get_thumbnail(
                self.image, self.get_small_thumbnail_dimensions, crop="center", quality=80, format="JPEG"
            )

        return _get_small_thumbnail()

    @cached_property
    def get_small_thumbnail_webp(self):
        @cached_as(self)
        def _get_small_thumbnail_webp():
            return get_thumbnail(
                self.image, self.get_small_thumbnail_dimensions, crop="center", quality=80, format="WEBP"
            )

        return _get_small_thumbnail_webp()

    @cached_property
    def image_tag(self):
        if self.image:
            return mark_safe(f'<img src="{escape(self.get_small_thumbnail.url)}" />')
        return ""

    image_tag.short_description = "Image"
    image_tag.allow_tags = True


class BackgroundImageManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type="b")


class PostImageManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type="p")

    def create(self, *args, **kwargs):
        kwargs.update({"type": "p"})
        return super().create(*args, **kwargs)


class BgImage(Image):
    objects = BackgroundImageManager()

    class Meta:
        verbose_name = "background image"
        proxy = True


class PostImage(Image):
    objects = PostImageManager()

    class Meta:
        verbose_name = "post image"
        proxy = True
