from django.apps import AppConfig


class BoardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "boards"

    def ready(self):
        from simple_history import register

        import boards.signals  # noqa
        from boards.models import Post

        register(Post)
