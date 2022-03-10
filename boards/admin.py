from django.contrib import admin

from .models import Board, BoardPreferences, Image, Post, Topic

# Register your models here.

admin.site.site_header = "Jotlet Administration"


class BoardPreferencesInline(admin.TabularInline):
    model = BoardPreferences
    extra = 0


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 1


class PostInline(admin.TabularInline):
    model = Post
    extra = 1


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "description",
        "owner",
        "uuid",
        "created_at",
        "updated_at",
    )
    fields = (
        "title",
        "description",
        "owner",
    )
    inlines = [TopicInline, BoardPreferencesInline]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("subject", "board", "created_at", "updated_at")
    fields = (
        "subject",
        "board",
    )
    inlines = [PostInline]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("content", "topic", "created_at", "updated_at")
    fields = (
        "content",
        "topic",
    )


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("title", "get_board_usage_count", "created_at", "updated_at")
    fields = ("image_tag", "title", "attribution", "image", "type")

    readonly_fields = ["image_tag"]

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ["image"]
        return self.readonly_fields
