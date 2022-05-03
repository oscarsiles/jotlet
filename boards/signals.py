from cacheops import invalidate_obj
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django_cleanup.signals import cleanup_pre_delete
from django_q.tasks import async_task
from sorl.thumbnail import delete

from .models import Board, BoardPreferences, Image, Post, Reaction, Topic
from .utils import channel_group_send


def invalidate_board_cache(board):
    invalidate_obj(board)
    key = make_template_fragment_key("board-list-post-count", [board.pk])

    if cache.get(key) is not None:
        cache.delete(key)


def invalidate_topic_cache(topic):
    invalidate_obj(topic)
    if Board.objects.filter(id=topic.board_id).exists():
        invalidate_board_cache(topic.board)


def invalidate_post_cache(post):
    invalidate_obj(post)
    if Topic.objects.filter(id=post.topic_id).exists():
        invalidate_topic_cache(post.topic)


@receiver(post_save, sender=Board)
def create_board_preferences(sender, instance, created, **kwargs):
    if created:
        BoardPreferences.objects.create(board=instance)


@receiver(post_save, sender=BoardPreferences)
def board_preferences_send_message(sender, instance, created, **kwargs):
    channel_group_send(
        f"board_{instance.board.slug}",
        {
            "type": "board_preferences_changed",
        },
    )


@receiver(post_save, sender=BoardPreferences)
@receiver(post_delete, sender=BoardPreferences)
def invalidate_board_preferences_cache(sender, instance, **kwargs):
    keyBoardPreferences1 = make_template_fragment_key("board-preferences-style", [instance.id])
    try:
        if cache.get(keyBoardPreferences1):
            cache.delete(keyBoardPreferences1)

        invalidate_obj(instance.board)
        for topic in instance.board.topics.all():
            invalidate_obj(topic)
            for post in topic.posts.all():
                invalidate_obj(post)
    except:
        raise Exception(f"Could not delete cache: board-{instance.id}")


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
    try:
        if Board.objects.filter(id=instance.board_id).exists():
            channel_group_send(
                f"board_{instance.board.slug}",
                {
                    "type": "topic_deleted",
                    "topic_pk": instance.pk,
                },
            )
    except:
        raise Exception(f"Could not send message: topic_deleted for topic {instance.pk}")


@receiver(post_save, sender=Topic)
@receiver(post_delete, sender=Topic)
def invalidate_topic_template_cache(sender, instance, **kwargs):
    try:
        invalidate_topic_cache(instance)
    except:
        raise Exception(f"Could not delete cache: topic-{instance.pk}")


@receiver(post_save, sender=Post)
@receiver(post_delete, sender=Post)
def invalidate_board_post_count(sender, instance, **kwargs):
    try:
        invalidate_post_cache(instance)
        if Topic.objects.filter(id=instance.topic_id).exists():
            key = make_template_fragment_key("board-list-post-count", [instance.topic.board.id])

            if cache.get(key) is not None:
                cache.delete(key)
    except:
        raise Exception(f"Could not delete cache: post-{instance.pk}")


@receiver(post_save, sender=Post)
def post_send_message(sender, instance, created, **kwargs):
    board_slug = instance.topic.board.slug
    if created:
        channel_group_send(
            f"board_{board_slug}",
            {
                "type": "post_created",
                "topic_pk": instance.topic.pk,
                "post_pk": instance.pk,
                "fetch_url": reverse("boards:post-fetch", kwargs={"slug": board_slug, "pk": instance.pk}),
            },
        )
    else:
        channel_group_send(
            f"board_{board_slug}",
            {
                "type": "post_updated",
                "topic_pk": instance.topic.pk,
                "post_pk": instance.pk,
            },
        )


@receiver(post_delete, sender=Post)
def post_delete_send_message(sender, instance, **kwargs):
    try:
        if Topic.objects.filter(id=instance.topic_id).exists():
            channel_group_send(
                f"board_{instance.topic.board.slug}",
                {
                    "type": "post_deleted",
                    "post_pk": instance.pk,
                },
            )
    except:
        raise Exception(f"Could not send message: post_deleted for post-{instance.pk}")


@receiver(post_save, sender=Reaction)
@receiver(post_delete, sender=Reaction)
def invalidate_post_cache_on_reaction(sender, instance, **kwargs):
    try:
        invalidate_obj(instance)
        invalidate_obj(instance.post)
        invalidate_obj(instance.post.topic)
        invalidate_obj(instance.post.topic.board)

    except:
        raise Exception(f"Could not invalidate cache: post-{instance.post.pk}-footer")


@receiver(post_save, sender=Image)
def create_thumbnail(sender, instance, created, **kwargs):
    if created:
        async_task("boards.tasks.create_thumbnails", instance)


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
