from django.core.management.base import BaseCommand
from django.template.defaultfilters import pluralize

from boards.models import Board, Image, Post


class Command(BaseCommand):
    help = "Match post to image and delete orphan images."

    def delete_orphan_image(self, img, count_orphans):
        img.delete()
        return count_orphans + 1

    def handle(self, *args, **kwargs):
        matched_count = 0
        orphan_count = 0
        images = Image.objects.filter(image_type="p").order_by("-board__created_at")
        total_image_count = images.count()
        boards = Board.objects.filter(id__in=images.values_list("board_id", flat=True).distinct())
        for board in boards:
            posts = Post.objects.filter(topic__board=board).order_by("-created_at")
            imgs = images.filter(board=board)
            for img in imgs:
                if img.post is None:
                    if matched_posts := [post for post in posts if img.image.url in post.content]:
                        img.post = matched_posts[0]
                        img.save()
                        matched_count += 1
                    else:
                        orphan_count = self.delete_orphan_image(img, orphan_count)
                elif img.image.url not in img.post.content:
                    orphan_count = self.delete_orphan_image(img, orphan_count)

        self.stdout.write(self.style.SUCCESS(f"{total_image_count} total post image{pluralize(total_image_count)}."))
        self.stdout.write(
            self.style.SUCCESS(
                f"{matched_count} image{pluralize(matched_count)} matched to post{pluralize(matched_count)}."
            )
        )
        self.stdout.write(self.style.SUCCESS(f"{orphan_count} orphan image{pluralize(orphan_count)} deleted."))
