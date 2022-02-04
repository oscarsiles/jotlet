from django.apps import AppConfig


class BoardsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'boards'

    def ready(self):
        try:
            # important do the import inside the method
            from django.contrib.auth.models import Group, Permission

            moderators, created = Group.objects.get_or_create(name='moderator') # create moderator group
            permission = Permission.objects.get_or_create(codename='can_delete_post')[0] # get delete post permission permission
            moderators.permissions.add(permission) # add permission to moderators group

        except:
            pass
