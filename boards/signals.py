import os

from cacheops import invalidate_obj
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_cleanup.signals import cleanup_pre_delete
from django_q.tasks import async_task
from sorl.thumbnail import delete

from boards.apps import BoardsConfig

from .models import Board, BoardPreferences, Image, Post, Topic
from .utils import channel_group_send


def populate_models(sender, **kwargs):
    moderators, created = Group.objects.get_or_create(name="Moderators")
    content_type = ContentType.objects.get(app_label=BoardsConfig.name, model="post")

    permissions = list(Permission.objects.filter(content_type=content_type))

    custom_permissions = ["add_board"]
    for custom_perm in custom_permissions:
        custom_perm = Permission.objects.get(content_type__app_label=BoardsConfig.name, codename=custom_perm)
        permissions.append(custom_perm)

    for perm in permissions:
        moderators.permissions.add(perm)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def add_default_user_permissions(sender, instance, created, **kwargs):
    if created:
        perm_list = ["add_board"]
        for perm in perm_list:
            perm = Permission.objects.get(content_type__app_label=BoardsConfig.name, codename=perm)
            instance.user_permissions.add(perm)


@receiver(post_save, sender=Board)
def create_board_preferences(sender, instance, created, **kwargs):
    if created:
        BoardPreferences.objects.create(board=instance)


@receiver(post_save, sender=BoardPreferences)
def approve_all_posts(sender, instance, created, **kwargs):
    posts = Post.objects.filter(topic__board=instance.board)
    for post in posts:
        invalidate_obj(post)
        if not instance.require_approval:  # approval turned off - approve all posts
            post.approved = True
            post.save()


@receiver(post_save, sender=BoardPreferences)
def board_preferences_send_message(sender, instance, created, **kwargs):
    channel_group_send(
        f"board_{instance.board.slug}",
        {
            "type": "board_preferences_changed",
        },
    )


@receiver(post_save, sender=BoardPreferences)
def invalidate_board_preferences_cache(sender, instance, created, **kwargs):
    keyBoardPreferences1 = make_template_fragment_key("board-preferences-style", [instance.pk])
    try:
        if cache.get(keyBoardPreferences1):
            cache.delete(keyBoardPreferences1)
    except:
        raise Exception(f"Could not delete cache: board-{instance.pk}")


@receiver(post_save, sender=Topic)
def topic_send_message(sender, instance, created, **kwargs):
    if created:
        message_type = "topic_created"
    else:
        message_type = "topic_updated"

    channel_group_send(
        f"board_{instance.board.slug}",
        {
            "type": message_type,
            "topic_pk": instance.pk,
        },
    )


@receiver(post_delete, sender=Topic)
def topic_delete_send_message(sender, instance, **kwargs):
    channel_group_send(
        f"board_{instance.board.slug}",
        {
            "type": "topic_deleted",
            "topic_pk": instance.pk,
        },
    )


@receiver(post_save, sender=Topic)
def invalidate_topic_template_cache(sender, instance, created, **kwargs):
    keyTopic1 = make_template_fragment_key("topic", [instance.pk])
    keyTopic2 = make_template_fragment_key("topic-buttons", [instance.pk])
    keyTopic3 = make_template_fragment_key("topic-create-post", [instance.pk])
    keyTopic4 = make_template_fragment_key("topic-newCard", [instance.pk])
    try:
        if cache.get(keyTopic1) is not None:
            cache.delete(keyTopic1)
        if cache.get(keyTopic2) is not None:
            cache.delete(keyTopic2)
        if cache.get(keyTopic3) is not None:
            cache.delete(keyTopic3)
        if cache.get(keyTopic4) is not None:
            cache.delete(keyTopic4)
    except:
        raise Exception(f"Could not delete cache: topic-{instance.pk}")


@receiver(post_save, sender=Post)
def post_send_message(sender, instance, created, **kwargs):
    if created:
        message_type = "post_created"
    else:
        message_type = "post_updated"

    channel_group_send(
        f"board_{instance.topic.board.slug}",
        {
            "type": message_type,
            "topic_pk": instance.topic.pk,
            "post_pk": instance.pk,
        },
    )


@receiver(post_delete, sender=Post)
def post_delete_send_message(sender, instance, **kwargs):
    channel_group_send(
        f"board_{instance.topic.board.slug}",
        {
            "type": "post_deleted",
            "post_pk": instance.pk,
        },
    )


@receiver(post_save, sender=Post)
def invalidate_post_template_cache(sender, instance, created, **kwargs):
    keyPost1 = make_template_fragment_key("post-content", [instance.pk])
    keyPost2 = make_template_fragment_key("post-buttons", [instance.pk])
    keyPost3 = make_template_fragment_key("post-approve-button", [instance.pk, instance.approved])
    try:
        if cache.get(keyPost1) is not None:
            cache.delete(keyPost1)
        if cache.get(keyPost2) is not None:
            cache.delete(keyPost2)
        if cache.get(keyPost3) is not None:
            cache.delete(keyPost3)
    except:
        raise Exception(f"Could not delete cache: post-{instance.pk}")


@receiver(post_save, sender=Image)
def create_thumbnail(sender, instance, created, **kwargs):
    if created:
        async_task("boards.tasks.create_thumbnail", instance)


@receiver(post_save, sender=Image)
@receiver(post_delete, sender=Image)
def update_image_select(sender, instance, **kwargs):
    keyImageSelect1 = make_template_fragment_key("image-select", [instance.type])
    keyImageSelect2 = make_template_fragment_key("image-select-image", [instance.pk])
    try:
        if cache.get(keyImageSelect1) is not None:
            cache.delete(keyImageSelect1)
        if cache.get(keyImageSelect2) is not None:
            cache.delete(keyImageSelect2)
    except:
        raise Exception(f"Could not delete cache: image-select-{instance.type}")


@receiver(cleanup_pre_delete)
def sorl_delete(**kwargs):
    delete(kwargs["file"])
