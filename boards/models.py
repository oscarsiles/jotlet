import uuid
from hashlib import blake2b

import auto_prefetch
from cacheops import cached_as
from django.conf import settings
from django.contrib.postgres.indexes import BrinIndex, GinIndex, OpClass
from django.db import IntegrityError, models
from django.db.models.functions import Upper
from django.template.defaultfilters import date
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import format_html
from sorl.thumbnail import get_thumbnail
from tree_queries.models import TreeNode
from tree_queries.query import TreeQuerySet

from jotlet.mixins.refresh_from_db_invalidates_cached_properties import InvalidateCachedPropertiesMixin

from .tasks import create_thumbnails, post_image_cleanup
from .utils import (
    generate_csv,
    get_export_upload_path,
    get_image_upload_path,
    get_is_moderator,
    get_random_string,
    process_image,
)

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

IMAGE_FORMATS = ["png", "jpeg", "bmp", "gif"]


class Board(InvalidateCachedPropertiesMixin, auto_prefetch.Model):
    title = models.CharField(max_length=50)
    slug = models.SlugField(max_length=8, unique=True, null=False)
    description = models.CharField(max_length=100, blank=True)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="boards"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    locked = models.BooleanField(default=False)

    class Meta(auto_prefetch.Model.Meta):
        permissions = (
            ("can_view_all_boards", "Can view all boards"),
            ("lock_board", "Can (un)lock all boards"),
        )
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
        ordering = ["created_at"]

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
                        if errors > 5:  # noqa: PLR2004
                            # tried 5 times, no dice. raise the integrity error and handle elsewhere
                            raise
                        self.slug = get_random_string(max_length)
                    else:
                        success = True
            else:
                super().save(*args, **kwargs)
            BoardPreferences.objects.create(board=self)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title}"

    @cached_property
    def get_posts(self):
        return Post.objects.filter(topic__board=self)

    @cached_property
    def get_post_count(self):
        return self.get_posts.count()

    get_post_count.short_description = "Post Count"

    @cached_property
    def get_unapproved_post_count(self):
        return self.get_posts.filter(approved=False).count()

    @cached_property
    def get_last_post_date(self):
        if self.get_post_count > 0:
            return date(self.get_posts.first().created_at, "d/m/Y")
        return None

    get_last_post_date.short_description = "Last Post Date"

    @cached_property
    def get_postimage_count(self):
        return Image.objects.filter(board=self, image_type="p").count()

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
        return is_allowed and not self.locked

    @cached_property
    def is_additional_data_allowed(self):
        return self.preferences.enable_chemdoodle  # currently only have chemdoodle additional data


class BoardPreferences(InvalidateCachedPropertiesMixin, auto_prefetch.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    board = auto_prefetch.OneToOneField(Board, on_delete=models.CASCADE, related_name="preferences")
    board_type = models.CharField(max_length=1, choices=BOARD_TYPE, default="d")
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
    enable_chemdoodle = models.BooleanField(default=False)
    enable_identicons = models.BooleanField(default=True)
    require_post_approval = models.BooleanField(default=False)
    allow_post_editing = models.BooleanField(default=True)
    require_post_reapproval_on_edit = models.BooleanField(default=False)
    allow_guest_replies = models.BooleanField(default=False)
    allow_image_uploads = models.BooleanField(default=False)
    moderators = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="moderated_boards")
    reaction_type = models.CharField(max_length=1, choices=REACTION_TYPE, default="n")
    posting_allowed_from = models.DateTimeField(null=True, blank=True)
    posting_allowed_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(auto_prefetch.Model.Meta):
        indexes = [
            BrinIndex(fields=["posting_allowed_from"], autosummarize=True),
            BrinIndex(fields=["posting_allowed_until"], autosummarize=True),
        ]

    def __str__(self):
        return f"{self.board.title} preferences"

    def save(self, *args, **kwargs):
        if self.background_type == "c" or (
            self.background_image.image_type != "b" if self.background_image is not None else True
        ):
            self.background_image = None
        if self.background_type == "b" and self.background_image is None:
            self.background_type = "c"
        super().save(*args, **kwargs)

    @cached_property
    def get_inverse_opacity(self):
        return round(1.0 - self.background_opacity, 2)

    def get_absolute_url(self):
        return reverse("boards:board-preferences", kwargs={"slug": self.board.slug})


class Topic(InvalidateCachedPropertiesMixin, auto_prefetch.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.TextField(max_length=400)
    board = auto_prefetch.ForeignKey(Board, on_delete=models.CASCADE, null=True, related_name="topics")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    locked = models.BooleanField(default=False)
    posts: "models.QuerySet[Post]"

    class Meta(auto_prefetch.Model.Meta):
        indexes = [
            BrinIndex(fields=["created_at"], autosummarize=True),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.subject}"

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
    def get_unapproved_post_count(self):
        return self.get_posts.filter(approved=False).count()

    @cached_property
    def get_last_post_date(self):
        if self.get_post_count > 0:
            return date(self.get_posts.first().created_at, "d/m/Y")
        return None

    get_last_post_date.short_description = "Last Post Date"

    @cached_property
    def is_locked(self):
        return self.locked or self.board.locked

    @cached_property
    def is_posting_allowed(self):
        return not self.is_locked and self.board.is_posting_allowed

    def post_create_allowed(self, request):
        @cached_as(self, extra=request.session.session_key, timeout=60 * 60 * 24)
        def _post_create_allowed(self, request):
            is_locked = self.is_locked
            return ((self.board.is_posting_allowed or request.user == self.board.owner) and not is_locked) or (
                request.user.is_staff or get_is_moderator(request.user, self.board)
            )

        return _post_create_allowed(self, request)

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"slug": self.board.slug})


class Post(InvalidateCachedPropertiesMixin, auto_prefetch.Model, TreeNode):
    objects = TreeQuerySet.as_manager(with_tree_fields=True)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.TextField(max_length=1000)
    topic = auto_prefetch.ForeignKey(Topic, on_delete=models.CASCADE, null=True, related_name="posts")
    user = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="posts"
    )
    session_key = models.CharField(max_length=40, blank=True)
    identity_hash = models.CharField(max_length=64, blank=True)
    approved = models.BooleanField(default=True)
    allow_replies = models.BooleanField(default=True)  # TODO: use to override single post reply permission
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(auto_prefetch.Model.Meta):
        indexes = [
            BrinIndex(fields=["created_at"], autosummarize=True),
        ]
        ordering = ["created_at"]
        permissions = (("can_approve_posts", "Can approve posts"),)

    def __str__(self):
        return f"{self.content}"

    def save(self, *args, **kwargs):
        prev_post = None
        if not self._state.adding:
            prev_post = Post.objects.get(pk=self.pk)
        else:
            string = self.user.username if self.user is not None else self.session_key
            salt = str(self.topic.board.id)
            self.identity_hash = blake2b(f"{string}{salt}".encode(), digest_size=32).hexdigest()
        super().save(*args, **kwargs)

        if self.topic.board.preferences.allow_image_uploads:
            cleanup_task = prev_post is None or prev_post.content != self.content
            if cleanup_task:
                post_image_cleanup(self, PostImage.objects.filter(board=self.topic.board))()

    def update_allowed(self, request):
        @cached_as(self, extra=request.session.session_key, timeout=60 * 60 * 24)
        def _update_allowed(self, request):
            is_locked = (
                self.topic.locked or self.topic.board.locked or not self.topic.board.preferences.allow_post_editing
            )
            return (
                (
                    request.session.session_key == self.session_key
                    or request.user == self.user
                    or request.user.has_perm("boards.change_post")
                )
                and not is_locked
            ) or get_is_moderator(request.user, self.topic.board)

        return _update_allowed(self, request)

    def reply_create_allowed(self, request):
        @cached_as(self, extra=request.session.session_key, timeout=60 * 60 * 24)
        def _reply_create_allowed(self, request):
            return self.topic.board.preferences.board_type == "r" and (
                (self.approved and self.topic.board.preferences.allow_guest_replies)
                or get_is_moderator(request.user, self.topic.board)
            )

        return _reply_create_allowed(self, request)

    def get_is_owner(self, request):
        @cached_as(self, extra=request.session.session_key, timeout=60 * 60 * 24)
        def _get_is_owner():
            return (self.session_key == request.session.session_key and self.session_key is not None) or (
                request.user.is_authenticated and self.user == request.user
            )

        return _get_is_owner()

    def get_reactions(self, reaction_type=None):
        @cached_as(self, extra=reaction_type, timeout=60 * 60 * 24)
        def _get_reactions(reaction_type):
            if reaction_type is None:
                reaction_type = self.get_reaction_type
            return Reaction.objects.filter(post=self, reaction_type=reaction_type)

        return _get_reactions(reaction_type)

    @cached_property
    def get_additional_data_count(self):
        @cached_as(self.additional_data.all(), timeout=60 * 60 * 24)
        def _get_additional_data_count():
            if AdditionalData.objects.filter(post=self).exists():
                return AdditionalData.objects.filter(post=self).count()
            return 0

        return _get_additional_data_count()

    def get_additional_data(self, additional_data_type="m"):
        @cached_as(self.additional_data.all(), extra=additional_data_type, timeout=60 * 60 * 24)
        def _get_additional_data(additional_data_type):
            if self.get_additional_data_count > 0:
                return AdditionalData.objects.get(post=self, data_type=additional_data_type)
            return None

        return _get_additional_data(additional_data_type)

    @cached_property
    def get_descendant_count(self):
        @cached_as(self, timeout=60 * 60 * 24)
        def _get_desdendant_count():
            return self.descendants().count()

        return _get_desdendant_count()

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
            count = reactions.count()
            match reaction_type:
                case "l":
                    return count
                case "v":
                    positive_count = sum(reaction.reaction_score == 1 for reaction in reactions)
                    negative_count = sum(reaction.reaction_score == -1 for reaction in reactions)
                    return positive_count, negative_count
                case "s":
                    if count != 0:
                        sumvar = sum(reaction.reaction_score for reaction in reactions)
                        return f"{(sumvar / count):.2g}"
                    return ""
                case _:
                    return 0

        return _get_reaction_score(reactions, reaction_type)

    def get_has_reacted(self, request, post_reactions=None):
        if post_reactions is None:
            post_reactions = self.get_reactions()

        has_reacted = False
        reaction_id = None
        reacted_score = 1  # default score

        @cached_as(post_reactions, timeout=60 * 60 * 24)
        def _get_has_reacted(attribute, value):
            for reaction in post_reactions:
                if getattr(reaction, attribute) == value:
                    return True, reaction.pk, reaction.reaction_score
            return has_reacted, reaction_id, reacted_score

        if post_reactions:
            if request.session.session_key:
                has_reacted, reaction_id, reacted_score = _get_has_reacted("session_key", request.session.session_key)

            if request.user.is_authenticated and not has_reacted:
                has_reacted, reaction_id, reacted_score = _get_has_reacted("user", request.user)

        return has_reacted, reaction_id, reacted_score

    def get_absolute_url(self):
        return reverse("boards:board", kwargs={"slug": self.topic.board.slug})


class Reaction(InvalidateCachedPropertiesMixin, auto_prefetch.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = auto_prefetch.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions")
    user = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reactions"
    )
    session_key = models.CharField(max_length=40, null=False, blank=False)
    reaction_type = models.CharField(max_length=1, choices=REACTION_TYPE, default="l")
    reaction_score = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(auto_prefetch.Model.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["post", "session_key", "reaction_type"], name="unique_anonymous_reaction"
            ),
            models.UniqueConstraint(fields=["post", "user", "reaction_type"], name="unique_user_reaction"),
        ]


ADDITIONAL_DATA_TYPE = (
    ("c", "chemdoodle"),
    ("f", "file"),
    ("m", "misc"),
)


class AdditionalData(InvalidateCachedPropertiesMixin, auto_prefetch.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = auto_prefetch.ForeignKey(Post, on_delete=models.CASCADE, related_name="additional_data")
    data_type = models.CharField(max_length=1, choices=ADDITIONAL_DATA_TYPE, default="m", editable=False)
    json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(auto_prefetch.Model.Meta):
        constraints = [
            models.UniqueConstraint(fields=["post", "data_type"], name="unique_post_additional_data_type"),
        ]


class Image(InvalidateCachedPropertiesMixin, auto_prefetch.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=50, db_index=True)
    attribution = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to=get_image_upload_path)

    image_type = models.CharField(max_length=1, choices=IMAGE_TYPE, default="b", help_text="Image type")
    board = auto_prefetch.ForeignKey(Board, on_delete=models.CASCADE, null=True, blank=True, related_name="images")
    post = auto_prefetch.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name="images")

    class Meta(auto_prefetch.Model.Meta):
        indexes = [
            BrinIndex(fields=["created_at"], autosummarize=True),
        ]
        ordering = ["title", "created_at"]

    def __str__(self):
        return f"{self.title or str(self.id)}"

    def save(self, *args, **kwargs):
        created = self._state.adding
        if created:
            self.image = process_image(self.image, self.image_type)
        super().save(*args, **kwargs)

        if created and self.image_type == "b":
            create_thumbnails(self)()

    @cached_property
    def get_board_usage_count(self):
        return BoardPreferences.objects.filter(background_type="i", background_image=self).count()

    get_board_usage_count.short_description = "Board Usage Count"

    @cached_property
    def get_image_dimensions(self):
        return f"{self.image.width}x{self.image.height}"

    @cached_property
    def get_image_file_exists(self):
        @cached_as(self, timeout=60 * 60 * 24)
        def _get_image_file_exists():
            return self.image.storage.exists(self.image.name)

        return _get_image_file_exists()

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
            return format_html('<img src="{}" />', self.get_small_thumbnail.url)
        return ""

    image_tag.short_description = "Image"
    image_tag.allow_tags = True


class BackgroundImageManager(auto_prefetch.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(image_type="b")

    def create(self, *args, **kwargs):
        kwargs["image_type"] = "b"
        return super().create(*args, **kwargs)


class PostImageManager(auto_prefetch.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(image_type="p")

    def create(self, *args, **kwargs):
        kwargs["image_type"] = "p"
        return super().create(*args, **kwargs)


class BgImage(Image):
    objects = BackgroundImageManager()

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "background image"
        proxy = True


class PostImage(Image):
    objects = PostImageManager()

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "post image"
        proxy = True


class Export(InvalidateCachedPropertiesMixin, auto_prefetch.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    board = auto_prefetch.ForeignKey(Board, on_delete=models.CASCADE, related_name="exports", null=False)
    file = models.FileField(upload_to=get_export_upload_path, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta(auto_prefetch.Model.Meta):
        indexes = [
            BrinIndex(fields=["created_at"], autosummarize=True),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file.name}"

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.generate_and_set_file()
            # only want to save the file when it is first created
            super().save(*args, **kwargs)

    def generate_and_set_file(self):
        header, posts = self.get_export_data()
        self.file = generate_csv(header, posts)

    def get_export_data(self):
        header = [
            "id",
            "content",
            "parent",
            "topic",
            "identity_hash",
            "approved",
            "created_at",
            "updated_at",
        ]
        posts = self.board.get_posts.values(*header)

        return header, posts
