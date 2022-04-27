from django.contrib.auth.models import Permission, User
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def add_default_user_permissions(sender, instance, created, **kwargs):
    if created:
        perm_list = ["add_board"]
        for perm in perm_list:
            perm = Permission.objects.get(content_type__app_label="boards", codename=perm)
            instance.user_permissions.add(perm)
