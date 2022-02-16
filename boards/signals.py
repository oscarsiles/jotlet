import os

from django.core.cache import cache, caches
from django.core.cache.utils import make_template_fragment_key
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_cleanup.signals import cleanup_pre_delete
from sorl.thumbnail import delete

from .models import Board, BoardPreferences, Post, Topic

cache_redis = caches["redis-cache"]


@receiver(post_save, sender=Board)
def create_board_preferences(sender, instance, created, **kwargs):
    if created:
        BoardPreferences.objects.create(board=instance)


@receiver(post_save, sender=BoardPreferences)
def approve_all_posts(sender, instance, created, **kwargs):
    if not instance.require_approval:  # approval turned off - approve all posts
        posts = Post.objects.filter(topic__board=instance.board).filter(approved=False)
        for post in posts:
            post.approved = True
            post.save()


@receiver(post_save, sender=Post)
def post_saved(sender, instance, created, **kwargs):
    keyPost = make_template_fragment_key("post", [instance.pk])
    try:
        cache_redis.delete(keyPost)
    except:
        raise Exception(f"Could not delete cache: post-{instance.pk}")


@receiver(cleanup_pre_delete)
def sorl_delete(**kwargs):
    delete(kwargs["file"])
