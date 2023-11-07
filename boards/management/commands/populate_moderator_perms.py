from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sets up initial permissions for moderators."

    def handle(self, *args, **kwargs):
        moderators, _ = Group.objects.get_or_create(name="Moderators")
        content_type = ContentType.objects.get(app_label="boards", model="post")

        permissions = list(Permission.objects.filter(content_type=content_type))

        custom_permission_names = ["add_board"]
        for custom_perm_name in custom_permission_names:
            custom_perm = Permission.objects.get(content_type__app_label="boards", codename=custom_perm_name)
            permissions.append(custom_perm)

        for perm in permissions:
            if not moderators.permissions.filter(codename=perm.codename).exists():
                moderators.permissions.add(perm)
                self.stdout.write(f"Successfully added permission {perm.codename} to moderators.")
            else:
                self.stdout.write(f"Permission {perm.codename} already exists for moderators.")

        self.stdout.write(self.style.SUCCESS("Successfully added permissions for moderators."))
