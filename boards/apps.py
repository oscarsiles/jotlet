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

        try:
            from django_q.models import Schedule
            from django_q.tasks import schedule

            required_scheduled_tasks = [
                {"name": "jotlet.tasks.clear_sessions_command", "schedule_type": "H"},
                {"name": "boards.tasks.thumbnail_cleanup_command", "schedule_type": "H"},
            ]

            for task in required_scheduled_tasks:
                if not Schedule.objects.filter(func=task["name"]).exists():
                    schedule(task["name"], schedule_type=task["schedule_type"])
        except Exception as e:
            pass
