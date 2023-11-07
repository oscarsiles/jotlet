import re
import shutil
from itertools import product

import pytest
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from faker import Faker
from PIL import Image as PILImage
from PIL import ImageFile

from boards.models import IMAGE_FORMATS, IMAGE_TYPE
from boards.utils import get_image_upload_path, get_is_moderator, get_random_string, process_image


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

    @pytest.mark.parametrize("length", [5, 10, 15, 20, 25])
    def test_get_random_string(self, length):
        randstr = get_random_string(length)
        assert len(randstr) == length
        assert randstr.isalnum()


class TestImageUtils:
    @classmethod
    def teardown_class(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    @pytest.mark.parametrize(
        ("image_format", "image_type"),
        product(IMAGE_FORMATS, [image_type[0] for image_type in IMAGE_TYPE]),
    )
    def test_get_image_upload_path(self, board, image_factory, image_format, image_type):
        image_type_map = {
            "p": (board.slug, board),
            "default": ("[a-z0-9]{2}", None),
        }
        ext_map = {
            "gif": "jpg",
            "bmp": "jpg",
            "default": image_format,
        }

        sub1, board_value = image_type_map.get(image_type, image_type_map["default"])
        ext = ext_map.get(image_format, ext_map["default"])

        img = image_factory(
            board=board_value,
            image_type=image_type,
            image__format=image_format,
            image__filename=f"test.{image_format}",
        )

        assert img.board == board_value

        assert re.compile(rf"images/{image_type}/{sub1}/[a-z0-9]{{2}}/{img.id}.{ext}").search(
            get_image_upload_path(img, img.image.name)
        )

    @pytest.mark.parametrize(
        ("image_format", "image_type", "resolution"),
        product(
            IMAGE_FORMATS,
            [image_type[0] for image_type in IMAGE_TYPE],
            [
                (settings.MAX_IMAGE_HEIGHT + 100, settings.MAX_IMAGE_WIDTH),
                (settings.MAX_IMAGE_HEIGHT, settings.MAX_IMAGE_WIDTH + 100),
            ],
        ),
    )
    def test_process_image(self, resolution, image_format, image_type):
        height, width = resolution
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        fake = Faker()

        image = SimpleUploadedFile(
            name=f"{height}x{width}.{image_format}",
            content=fake.image(size=(height, width), image_format=image_format),
        )

        image = process_image(
            image,
            image_type=image_type,
            height=settings.MAX_IMAGE_HEIGHT,
            width=settings.MAX_IMAGE_WIDTH,
        )

        if image_type == "p":
            max_width = settings.MAX_POST_IMAGE_WIDTH
            max_height = settings.MAX_POST_IMAGE_HEIGHT
        else:
            max_width = settings.MAX_IMAGE_WIDTH
            max_height = settings.MAX_IMAGE_HEIGHT

        pilimage = PILImage.open(image)
        assert pilimage.width <= max_width
        assert pilimage.height <= max_height

        assert pilimage.mode == "RGB"
        if image_format not in ["jpeg", "png"]:
            assert pilimage.format == "JPEG"
