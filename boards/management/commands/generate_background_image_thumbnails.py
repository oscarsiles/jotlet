from django.core.management.base import BaseCommand, CommandError
from django.template.defaultfilters import pluralize

from boards.models import BgImage
from boards.tasks import create_thumbnails


class Command(BaseCommand):
    help = "Generate thumbnails for all background images in the database"

    def handle(self, *args, **kwargs):
        try:
            self.stdout.write(self.style.SUCCESS("Generating thumbnails..."))
            count = 0
            for image in BgImage.objects.all():
                self.stdout.write(f"Generating thumbnail for {image}")
                create_thumbnails(image)
                count += 1
            self.stdout.write(self.style.SUCCESS(f"Thumbnails generated for {count} image{pluralize(count)}."))
        except Exception as e:
            raise CommandError(f"Failed to generate thumbnails: {e}")
