from django.core.management.base import BaseCommand, CommandError
from django.template.defaultfilters import pluralize

from boards.models import Board, Image, Post


class Command(BaseCommand):
    help = "Match post to image and delete orphan images."

    def handle(self, *args, **kwargs):
        try:
            count_matched = 0
            count_orphans = 0
            images = Image.objects.filter(type="p").order_by("board__id")
            boards = Board.objects.filter(id__in=images.values_list("board_id", flat=True).distinct())
            for board in boards:
                posts = Post.objects.filter(topic__board=board).order_by("-created_at")
                imgs = images.filter(board=board)
                for img in imgs:
                    if img.post is None:
                        matched = False
                        for post in posts:
                            if img.image.url in post.content:
                                img.post = post
                                img.save()
                                count_matched += 1
                                matched = True
                                break
                        if not matched:
                            img.delete()
                            count_orphans += 1
                    else:
                        if img.image.url not in img.post.content:
                            img.delete()
                            count_orphans += 1

            count_images = Image.objects.filter(type="p").count()
            self.stdout.write(self.style.SUCCESS(f"{count_images} total post image{pluralize(count_images)}."))
            self.stdout.write(
                self.style.SUCCESS(
                    f"{count_matched} image{pluralize(count_matched)} matched to post{pluralize(count_matched)}."
                )
            )
            self.stdout.write(self.style.SUCCESS(f"{count_orphans} orphan image{pluralize(count_orphans)} deleted."))
        except Exception:
            raise CommandError("Failed to cleanup post images.")
