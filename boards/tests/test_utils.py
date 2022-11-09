import re
import shutil

import factory
from django.conf import settings
from django.contrib.auth.models import Permission
from PIL import Image as PILImage
from PIL import ImageFile

from boards.models import IMAGE_TYPE
from boards.utils import get_image_upload_path, get_is_moderator, get_random_string, process_image

from .test_models import IMAGE_FORMATS


class TestUtils:
    def test_get_is_moderator(self, board, user, user2, user3, user_staff):
        user3.user_permissions.add(
            Permission.objects.get(content_type__app_label="boards", codename="can_approve_posts")
        )

        assert not get_is_moderator(user2, board)  # not a moderator
        assert get_is_moderator(user, board)  # owner
        assert get_is_moderator(user3, board)  # has permission
        assert get_is_moderator(user_staff, board)  # staff

        board.preferences.moderators.add(user2)
        assert get_is_moderator(user2, board)

    def test_get_random_string(self):
        for i in range(20):  # arbitrary range
            randstr = get_random_string(i)
            assert len(randstr) == i
            assert re.compile(rf"^[a-z0-9]{{{i}}}$").search(randstr)


class TestImageUtils:
    @classmethod
    def teardown_class(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_get_image_upload_path(self, board, image_factory):
        for format in IMAGE_FORMATS:
            for type, _ in IMAGE_TYPE:
                img = image_factory(
                    board=board if type == "p" else None,
                    type=type,
                    image__format=format,
                    image__filename=f"test.{format}",
                )
                if type == "p":
                    sub1 = board.slug
                    assert img.board == board
                else:
                    sub1 = "[a-z0-9]{2}"
                    assert img.board is None

                if format in ["gif", "bmp"]:
                    ext = "jpg"
                else:
                    ext = format

                assert re.compile(rf"images/{type}/{sub1}/[a-z0-9]{{2}}/{img.uuid}.{ext}").search(
                    get_image_upload_path(img, img.image.name)
                )

    def test_process_image(self, image_factory):
        ImageFile.LOAD_TRUNCATED_IMAGES = True

        resolutions = [
            (settings.MAX_IMAGE_HEIGHT + 100, settings.MAX_IMAGE_WIDTH),
            (settings.MAX_IMAGE_HEIGHT, settings.MAX_IMAGE_WIDTH + 100),
        ]

        for height, width in resolutions:
            for format in IMAGE_FORMATS:
                for type, _ in IMAGE_TYPE:
                    img = image_factory(
                        image=factory.django.ImageField(
                            board=None,
                            filename=f"{height}x{width}.{format}",
                            height=height,
                            width=width,
                            format=format,
                            palette="P" if format == "bmp" else "RGB",
                        ),
                    )
                    img.image.open()  # fixes "ValueError: seek of closed file"
                    img.image = process_image(
                        img.image,
                        type=type,
                        height=settings.MAX_IMAGE_HEIGHT,
                        width=settings.MAX_IMAGE_WIDTH,
                    )

                    if type == "p":
                        max_width = settings.MAX_POST_IMAGE_WIDTH
                        max_height = settings.MAX_POST_IMAGE_HEIGHT
                    else:
                        max_width = settings.MAX_IMAGE_WIDTH
                        max_height = settings.MAX_IMAGE_HEIGHT

                    assert img.image.width <= max_width
                    assert img.image.height <= max_height

                    pilimage = PILImage.open(img.image)
                    assert pilimage.mode == "RGB"
                    if format not in ["jpeg", "png"]:
                        assert pilimage.format == "JPEG"
