from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from jotlet.admin import DisableDeleteInlineFormSet

from .models import Board, BoardPreferences, Image, Post, Topic


class BoardPreferencesInline(admin.StackedInline):
    model = BoardPreferences
    formset = DisableDeleteInlineFormSet
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "background_image":
            kwargs["queryset"] = Image.objects.filter(type="b")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0
    show_change_link = True
    fields = ("subject", "get_post_count", "get_last_post_date")
    readonly_fields = ("get_post_count", "get_last_post_date")


class PostInline(admin.TabularInline):
    model = Post
    extra = 0


@admin.register(Board)
class BoardAdmin(SimpleHistoryAdmin):
    list_display = (
        "title",
        "description",
        "owner",
        "get_post_count",
        "get_last_post_date",
        "get_image_count",
        "created_at",
    )
    fields = (
        "title",
        "description",
        "owner",
    )
    inlines = [TopicInline, BoardPreferencesInline]


@admin.register(Topic)
class TopicAdmin(SimpleHistoryAdmin):
    list_display = ("subject", "board", "get_post_count", "created_at", "updated_at")
    fields = ("subject", "board")
    readonly_fields = ["board"]
    inlines = [PostInline]


@admin.register(Post)
class PostAdmin(SimpleHistoryAdmin):
    list_display = ("content", "topic", "created_at", "updated_at")
    fields = ("content", "topic")


class BgImage(Image):
    class Meta:
        verbose_name_plural = "Images: Background"
        proxy = True


@admin.register(BgImage)
class ImageAdmin(SimpleHistoryAdmin):
    list_display = ("__str__", "get_board_usage_count", "created_at", "updated_at")
    fields = ("image_tag", "title", "attribution", "image", "type")

    readonly_fields = ["image_tag"]

    def get_queryset(self, request):
        return self.model.objects.filter(type="b")

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ["image", "type"]
        return self.readonly_fields


class PostImage(Image):
    class Meta:
        verbose_name_plural = "Images: Posts"
        proxy = True


@admin.register(PostImage)
class PostImageAdmin(SimpleHistoryAdmin):
    list_display = ("__str__", "board", "created_at")
    fields = ("image_tag", "image", "type", "board")

    readonly_fields = list(fields)

    def get_queryset(self, request):
        return self.model.objects.filter(type="p")
