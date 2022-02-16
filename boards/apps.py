from django.apps import AppConfig
from django.db.models.signals import post_migrate


class BoardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "boards"

    def ready(self):
        from .signals import populate_models

        populate_models(sender=self)
        # post_migrate.connect(populate_models, sender=self)
