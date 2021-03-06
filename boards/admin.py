from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from jotlet.admin import DisableDeleteInlineFormSet

from .models import Board, BoardPreferences, Image, Post, Topic


class BoardPreferencesInline(admin.StackedInline):
    model = BoardPreferences
    formset = DisableDeleteInlineFormSet
    extra = 0


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0
    fields = ("subject", "get_post_count", "get_last_post_date")
    readonly_fields = ("get_post_count", "get_last_post_date")


class PostInline(admin.TabularInline):
    model = Post
    extra = 1


@admin.register(Board)
class BoardAdmin(SimpleHistoryAdmin):
    list_display = (
        "title",
        "description",
        "owner",
        "get_post_count",
        "get_last_post_date",
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
    fields = (
        "subject",
        "board",
    )
    inlines = [PostInline]


@admin.register(Post)
class PostAdmin(SimpleHistoryAdmin):
    list_display = ("content", "topic", "created_at", "updated_at")
    fields = (
        "content",
        "topic",
    )


@admin.register(Image)
class ImageAdmin(SimpleHistoryAdmin):
    list_display = ("title", "get_board_usage_count", "created_at", "updated_at")
    fields = ("image_tag", "title", "attribution", "image", "type")

    readonly_fields = ["image_tag"]

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ["image"]
        return self.readonly_fields
