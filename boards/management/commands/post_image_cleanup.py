from django.core.management.base import BaseCommand, CommandError
from django.template.defaultfilters import pluralize

from boards.models import Board, Image, Post
from boards.tasks import post_image_cleanup_task


class Command(BaseCommand):
    help = "Match post to image and delete orphan images."

    def handle(self, *args, **kwargs):
        try:
            count_matched = 0
            count_orphans = 0
            images = Image.objects.filter(board__isnull=False, type="p").order_by("board__id")
            boards = Board.objects.filter(id__in=images.values_list("board_id", flat=True).distinct())
            for board in boards:
                posts = Post.objects.filter(topic__board=board).order_by("-created_at")
                imgs = images.filter(board=board)
                for post in posts:
                    result = post_image_cleanup_task(post, imgs)
                    if result == "matched":
                        count_matched += 1
                    elif result == "deleted":
                        count_orphans += 1

            count_images = Image.objects.filter(type="p").count()
            self.stdout.write(self.style.SUCCESS(f"{count_images} total post image{pluralize(count_images)}."))
            self.stdout.write(
                self.style.SUCCESS(
                    f"{count_matched} image{pluralize(count_matched)} matched to post{pluralize(count_matched)}."
                )
            )
            self.stdout.write(self.style.SUCCESS(f"{count_orphans} orphan image{pluralize(count_matched)} deleted."))
        except Exception:
            raise CommandError("Failed to cleanup post images.")
