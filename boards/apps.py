from django.apps import AppConfig


class BoardsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'boards'

    def ready(self):
        # important do the import inside the method
        from django.contrib.auth.models import Group

        Group.objects.get_or_create(name='moderator') # create moderator group
