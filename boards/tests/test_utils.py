import shutil
import tempfile

import factory
from django.conf import settings
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from PIL import Image as PILImage

from accounts.tests.factories import UserFactory
from boards.models import IMAGE_TYPE
from boards.utils import get_image_upload_path, get_is_moderator, get_random_string

from .factories import BoardFactory, ImageFactory
from .test_models import IMAGE_FORMATS

MEDIA_ROOT = tempfile.mkdtemp()


class UtilsTest(TestCase):
    def test_get_is_moderator(self):
        normal_user = UserFactory()
        owner_user = UserFactory()
        mod_user = UserFactory()
        perms_user = UserFactory()
        perms_user.user_permissions.add(
            Permission.objects.get(content_type__app_label="boards", codename="can_approve_posts")
        )
        staff_user = UserFactory(is_staff=True)

        board = BoardFactory(owner=owner_user)
        self.assertFalse(get_is_moderator(normal_user, board))
        self.assertFalse(get_is_moderator(mod_user, board))
        self.assertTrue(get_is_moderator(perms_user, board))
        self.assertTrue(get_is_moderator(owner_user, board))
        self.assertTrue(get_is_moderator(staff_user, board))

        board_mod = BoardFactory(owner=owner_user)
        board_mod.preferences.moderators.add(mod_user)
        self.assertFalse(get_is_moderator(normal_user, board_mod))
        self.assertTrue(get_is_moderator(mod_user, board_mod))
        self.assertTrue(get_is_moderator(perms_user, board_mod))
        self.assertTrue(get_is_moderator(owner_user, board_mod))
        self.assertTrue(get_is_moderator(staff_user, board_mod))

    def test_get_random_string(self):
        for i in range(20):  # arbitrary range
            randstr = get_random_string(i)
            self.assertEqual(len(randstr), i)
            self.assertRegex(randstr, rf"^[a-z0-9]{{{i}}}$")


@override_settings(
    MEDIA_ROOT=MEDIA_ROOT,
    # reduce resolution to speed up tests
    MAX_IMAGE_HEIGHT=500,
    MAX_IMAGE_WIDTH=500,
)
class TestImageUtils(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_get_image_upload_path(self):
        board = BoardFactory()
        for type, _ in IMAGE_TYPE:
            img = ImageFactory(board=board if type == "p" else None, type=type)
            if type == "p":
                sub1 = board.slug
                self.assertEqual(img.board, board)
            else:
                sub1 = "[a-z0-9]{2}"
                self.assertIsNone(img.board)

            self.assertRegex(
                get_image_upload_path(img, img.image.name),
                rf"images/{type}/{sub1}/[a-z0-9]{{2}}/{img.uuid}.png",
            )

    def test_process_image(self):
        from PIL import ImageFile

        from boards.utils import process_image

        ImageFile.LOAD_TRUNCATED_IMAGES = True

        resolutions = [
            (settings.MAX_IMAGE_HEIGHT + 100, settings.MAX_IMAGE_WIDTH),
            (settings.MAX_IMAGE_HEIGHT, settings.MAX_IMAGE_WIDTH + 100),
        ]

        for height, width in resolutions:
            for format in IMAGE_FORMATS:
                for type, _ in IMAGE_TYPE:
                    img = ImageFactory(
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

                    self.assertLessEqual(img.image.width, max_width)
                    self.assertLessEqual(img.image.height, max_height)

                    pilimage = PILImage.open(img.image)
                    self.assertEqual(pilimage.mode, "RGB")
                    if format not in ["jpeg", "png"]:
                        self.assertEqual(pilimage.format, "JPEG")
