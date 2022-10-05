from cacheops import invalidate_obj
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django_cleanup.signals import cleanup_pre_delete

from .models import BgImage, Board, BoardPreferences, Post, Reaction, Topic
from .tasks import delete_thumbnails
from .utils import channel_group_send


def invalidate_board_cache(board):
    invalidate_obj(board)
    key = make_template_fragment_key("board-list-post-count", [board.pk])

    if cache.get(key) is not None:
        cache.delete(key)


def invalidate_board_post_count_cache(instance):
    try:
        invalidate_post_cache(instance)
        if Topic.objects.filter(id=instance.topic_id).exists():
            key = make_template_fragment_key("board-list-post-count", [instance.topic.board.id])

            if cache.get(key) is not None:
                cache.delete(key)
    except Exception:
        raise Exception(f"Could not delete cache: post-{instance.pk}")


def invalidate_topic_cache(topic):
    invalidate_obj(topic)
    try:
        if topic.board:
            invalidate_board_cache(topic.board)
    except Board.DoesNotExist:
        pass


def invalidate_post_cache(post):
    invalidate_obj(post)
    try:
        if post.topic:
            invalidate_topic_cache(post.topic)
    except Topic.DoesNotExist:
        pass


def invalidate_reaction_cache(reaction):
    invalidate_obj(reaction)
    try:
        if reaction.post:
            invalidate_post_cache(reaction.post)
    except Post.DoesNotExist:
        pass


@receiver(post_save, sender=BoardPreferences)
def board_preferences_send_message(sender, instance, created, **kwargs):
    channel_group_send(
        f"board-{instance.board.slug}",
        {
            "type": "board_preferences_changed",
        },
    )


@receiver(post_save, sender=BoardPreferences)
@receiver(post_delete, sender=BoardPreferences)
def invalidate_board_preferences_cache(sender, instance, **kwargs):
    try:
        invalidate_obj(instance)
        invalidate_obj(instance.board)
        for topic in instance.board.topics.all():
            invalidate_obj(topic)
            for post in topic.posts.all():
                invalidate_obj(post)
    except Exception:
        raise Exception(f"Could not delete cache: board-{instance.id}")


@receiver(post_save, sender=Topic)
def topic_send_message(sender, instance, created, **kwargs):
    if created:
        message_type = "topic_created"
    else:
        message_type = "topic_updated"

    channel_group_send(
        f"board-{instance.board.slug}",
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
                f"board-{instance.board.slug}",
                {
                    "type": "topic_deleted",
                    "topic_pk": instance.pk,
                },
            )
    except Exception:
        raise Exception(f"Could not send message: topic_deleted for topic {instance.pk}")


@receiver(post_save, sender=Topic)
@receiver(post_delete, sender=Topic)
def invalidate_topic_template_cache(sender, instance, **kwargs):
    try:
        invalidate_topic_cache(instance)
    except Exception:
        raise Exception(f"Could not delete cache: topic-{instance.pk}")


@receiver(post_save, sender=Post)
def post_created_invalidate_cache(sender, instance, created, **kwargs):
    if created:
        invalidate_post_cache(instance)


@receiver(post_delete, sender=Post)
def post_deleted_invalidate_cache(sender, instance, **kwargs):
    invalidate_post_cache(instance)


@receiver(post_save, sender=Post)
def post_send_message(sender, instance, created, **kwargs):
    board_slug = instance.topic.board.slug
    if created and not instance.parent:
        channel_group_send(
            f"board-{board_slug}",
            {
                "type": "post_created",
                "topic_pk": instance.topic_id,
                "post_pk": instance.pk,
                "fetch_url": reverse(
                    "boards:post-fetch",
                    kwargs={
                        "slug": board_slug,
                        "topic_pk": instance.topic_id,
                        "pk": instance.pk,
                    },
                ),
            },
        )
    else:
        channel_group_send(
            f"board-{board_slug}",
            {
                "type": "post_updated",
                "topic_pk": instance.topic_id,
                "post_pk": instance.ancestors(include_self=True).first().pk,
            },
        )


@receiver(post_delete, sender=Post)
def post_delete_send_message(sender, instance, **kwargs):
    try:
        if Topic.objects.filter(id=instance.topic_id).exists():
            channel_group_send(
                f"board-{instance.topic.board.slug}",
                {
                    "type": "post_deleted",
                    "topic_pk": instance.topic_id,
                    "post_pk": instance.pk,
                },
            )
    except Exception:
        raise Exception(f"Could not send message: post_deleted for post-{instance.pk}")


@receiver(post_save, sender=Reaction)
@receiver(post_delete, sender=Reaction)
def invalidate_post_cache_on_reaction(sender, instance, **kwargs):
    invalidate_reaction_cache(instance)


@receiver(post_save, sender=BgImage)
@receiver(post_delete, sender=BgImage)
def invalidate_bg_image_cache(sender, instance, **kwargs):
    keyImageSelect1 = make_template_fragment_key("image-select", [instance.type])
    keyImageSelect2 = make_template_fragment_key("image-select-image", [instance.pk])
    try:
        invalidate_obj(instance)
        if cache.get(keyImageSelect1) is not None:
            cache.delete(keyImageSelect1)
        if cache.get(keyImageSelect2) is not None:
            cache.delete(keyImageSelect2)
    except Exception:
        raise Exception(f"Could not delete cache: image-select-{instance.type}")


@receiver(cleanup_pre_delete)
def sorl_delete(**kwargs):
    delete_thumbnails(kwargs["file"])()
