import contextlib
from importlib import import_module

from django.apps import AppConfig


class BoardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "boards"

    def ready(self):
        with contextlib.suppress(ImportError):
            import_module(f"{self.name}.signals")
