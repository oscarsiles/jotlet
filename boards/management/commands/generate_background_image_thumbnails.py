from django.core.management.base import BaseCommand
from django.template.defaultfilters import pluralize
from huey.contrib.djhuey import HUEY

from boards.models import BgImage
from boards.tasks import create_thumbnails


class Command(BaseCommand):
    help = "Generate thumbnails for all background images in the database"

    def handle(self, *args, **kwargs):
        HUEY.immediate = True
        self.stdout.write(self.style.SUCCESS("Generating thumbnails..."))
        count = 0
        for image in BgImage.objects.all():
            self.stdout.write(f"Generating thumbnail for {image}")
            create_thumbnails(image)()
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Thumbnails generated for {count} image{pluralize(count)}."))
