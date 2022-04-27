from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Sets up initial permissions for moderators."

    def handle(self, *args, **kwargs):
        try:
            moderators, _ = Group.objects.get_or_create(name="Moderators")
            content_type = ContentType.objects.get(app_label="boards", model="post")

            permissions = list(Permission.objects.filter(content_type=content_type))

            custom_permissions = ["add_board"]
            for custom_perm in custom_permissions:
                custom_perm = Permission.objects.get(content_type__app_label="boards", codename=custom_perm)
                permissions.append(custom_perm)

            for perm in permissions:
                moderators.permissions.add(perm)
        except:
            raise CommandError("Failed to populate moderator permissions.")
