from django.apps import AppConfig


class BoardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "boards"

    def ready(self):
        try:
            from .signals import populate_models

            populate_models(sender=self)
        except:
            pass
