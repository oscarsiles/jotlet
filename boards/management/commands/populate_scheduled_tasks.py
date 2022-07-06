from django.core.management.base import BaseCommand, CommandError
from django_q.models import Schedule
from django_q.tasks import schedule


class Command(BaseCommand):
    help = "Sets up initial scheduled tasks."

    def handle(self, *args, **kwargs):
        try:
            required_scheduled_tasks = [
                {"name": "jotlet.tasks.clear_sessions_command", "schedule_type": "H"},
                {"name": "accounts.tasks.axes_reset_logs", "schedule_type": "M"},
                {"name": "boards.tasks.thumbnail_cleanup_command", "schedule_type": "W"},
                {"name": "boards.tasks.history_clean_duplicates_past_hour_command", "schedule_type": "H"},
                {"name": "boards.tasks.history_clean_old_command", "schedule_type": "D"},
            ]

            for task in required_scheduled_tasks:
                if not Schedule.objects.filter(func=task["name"]).exists():
                    schedule(task["name"], schedule_type=task["schedule_type"])
                    self.stdout.write(f"Successfully scheduled {task['name']}.")
                else:
                    self.stdout.write(f"Scheduled task {task['name']} already exists.")
            self.stdout.write(self.style.SUCCESS("Successfully scheduled all required tasks."))
        except Exception:
            raise CommandError("Failed to populate scheduled tasks.")
