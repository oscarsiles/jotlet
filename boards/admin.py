from django.contrib import admin

from jotlet.admin import DisableDeleteInlineFormSet

from .models import BgImage, Board, BoardPreferences, Image, Post, PostImage, Topic


class BoardPreferencesInline(admin.StackedInline):
    model = BoardPreferences
    formset = DisableDeleteInlineFormSet
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "background_image":
            kwargs["queryset"] = Image.objects.filter(image_type="b")
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
class BoardAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "description",
        "owner",
        "get_post_count",
        "get_last_post_date",
        "get_postimage_count",
        "created_at",
    )
    fields = (
        "title",
        "description",
        "owner",
    )
    inlines = [TopicInline, BoardPreferencesInline]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("subject", "board", "get_post_count", "created_at", "updated_at")
    fields = ("subject", "board")
    readonly_fields = ["board"]
    inlines = [PostInline]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("content", "topic", "created_at", "updated_at")
    fields = ("content", "topic")


@admin.register(BgImage)
class BackgroundImageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "get_board_usage_count", "created_at", "updated_at")
    fields = ("image_tag", "title", "attribution", "image", "image_type")

    readonly_fields = ["image_tag", "image_type"]

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return [*self.readonly_fields, "image", "image_type"]
        return self.readonly_fields


@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "board", "created_at")
    fields = ("image_tag", "image", "image_type", "board")

    readonly_fields = list(fields)

    def has_add_permission(self, request, obj=None):
        return False
