from io import StringIO

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.template.defaultfilters import pluralize

from boards.models import Post, PostImage

# Test data
test_data = [
    # Test case ID: 1
    # Description: Happy path, single image
    # Expected: One thumbnail is generated
    {"image_count": 1, "expected_count": 1, "test_id": "single_image"},
    # Test case ID: 2
    # Description: Happy path, multiple images
    # Expected: Thumbnails are generated for all images
    {"image_count": 3, "expected_count": 3, "test_id": "multiple_images"},
    # Test case ID: 3
    # Description: Edge case, no images
    # Expected: No thumbnails are generated
    {"image_count": 0, "expected_count": 0, "test_id": "no_images"},
]


class TestGenerateBgImageThumbnails:
    @pytest.mark.parametrize("image_count", [0, 1, 2])
    def test_command(self, bg_image_factory, image_count):
        bg_image_factory.create_batch(image_count)

        out = StringIO()
        call_command("generate_background_image_thumbnails", stdout=out)

        assert f"Thumbnails generated for {image_count} image{pluralize(image_count)}." in out.getvalue()


class TestPopulateModeratorPerms:
    @pytest.mark.parametrize("group_exists", [(True), (False)])
    @pytest.mark.parametrize("perm_exists", [(True), (False)])
    def test_command(self, group_exists, perm_exists):
        moderators = Group.objects.create(name="Moderators")
        if not group_exists:
            moderators.delete()
        if group_exists and not perm_exists:
            moderators.permissions.filter(codename="add_board").delete()

        out = StringIO()
        call_command("populate_moderator_perms", stdout=out)

        moderators = Group.objects.filter(name="Moderators")
        assert moderators.count() == 1
        assert moderators.first().permissions.filter(codename="add_board").exists()


class TestPostImageCleanup:
    @pytest.mark.parametrize(
        ("image_count", "post_count", "matched_count", "orphan_count"),
        [
            (5, 5, 5, 0),  # all matched
            (5, 3, 3, 2),  # some orphans
            (5, 0, 0, 5),  # no posts
            (0, 5, 0, 0),  # no images
            (5, 5, 0, 5),  # no matches
        ],
    )
    def test_command(
        self, board, post_factory, post_image_factory, image_count, post_count, matched_count, orphan_count
    ):
        images = post_image_factory.create_batch(image_count, board=board)
        posts = post_factory.create_batch(post_count, topic__board=board)
        for i in range(min(matched_count, len(images), len(posts))):
            posts[i].content += images[i].image.url
            posts[i].save()

        out = StringIO()
        call_command("post_image_cleanup", stdout=out)
        out = out.getvalue()

        assert f"{image_count} total post image{pluralize(image_count)}." in out
        assert f"{orphan_count} orphan image{pluralize(orphan_count)} deleted." in out
        assert f"{matched_count} image{pluralize(matched_count)} matched to post{pluralize(matched_count)}." in out

        images = PostImage.objects.all()
        assert images.count() == matched_count
        assert Post.objects.filter(topic__board=board).count() == post_count
        for i in range(matched_count):
            assert images[i].post in posts
        for i in range(matched_count, len(images)):
            with pytest.raises(PostImage.DoesNotExist):
                images[i].refresh_from_db()
