from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import UserProfile


@receiver(post_save, sender=get_user_model())
def add_default_user_permissions(sender, instance, created, **kwargs):
    if created:
        perm_list = ["add_board"]
        for perm in perm_list:
            perm = Permission.objects.get(content_type__app_label="boards", codename=perm)
            instance.user_permissions.add(perm)


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
