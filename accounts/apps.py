import contextlib
from importlib import import_module

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        with contextlib.suppress(ImportError):
            import_module(f"{self.name}.signals")
