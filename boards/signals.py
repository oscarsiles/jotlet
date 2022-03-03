import os
from django.conf import settings

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from cacheops import invalidate_obj, invalidate_model, invalidate_all
from django_cleanup.signals import cleanup_pre_delete
from sorl.thumbnail import delete

from boards.apps import BoardsConfig

from .models import Board, BoardPreferences, Image, Post, Topic


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


@receiver(post_save, sender=Topic)
def topic_saved(sender, instance, created, **kwargs):
    keyTopic = make_template_fragment_key("topic", [instance.pk])
    try:
        if cache.get(keyTopic) is not None:
            cache.delete(keyTopic)
    except:
        raise Exception(f"Could not delete cache: topic-{instance.pk}")


@receiver(post_save, sender=Post)
def post_saved(sender, instance, created, **kwargs):
    keyPost = make_template_fragment_key("post", [instance.pk])
    try:
        cache.delete(keyPost)
    except:
        raise Exception(f"Could not delete cache: post-{instance.pk}")


@receiver(post_save, sender=Image)
@receiver(post_delete, sender=Image)
def update_image_select(sender, instance, **kwargs):
    keyImageSelect = make_template_fragment_key("image_select", [instance.type])
    try:
        cache.delete(keyImageSelect)
    except:
        raise Exception(f"Could not delete cache: image_select-{instance.type}")


@receiver(cleanup_pre_delete)
def sorl_delete(**kwargs):
    delete(kwargs["file"])
