import os
import shutil
import tempfile

from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image as PILImage

from boards.models import IMAGE_TYPE, Board, Image
from boards.utils import get_image_upload_path, get_is_moderator, get_random_string, process_image

MEDIA_ROOT = tempfile.mkdtemp()


class UtilsTest(TestCase):
    def test_get_is_moderator(self):
        normal_user = User.objects.create_user(username="normal_user", password="test")
        owner_user = User.objects.create_user(username="owner", password="test")
        mod_user = User.objects.create_user(username="moderator", password="test")
        perms_user = User.objects.create_user(username="perms", password="test")
        perms_user.user_permissions.add(
            Permission.objects.get(content_type__app_label="boards", codename="can_approve_posts")
        )
        staff_user = User.objects.create_user(username="staff", password="test", is_staff=True)

        board = Board.objects.create(title="Test Board", owner=owner_user)
        self.assertFalse(get_is_moderator(normal_user, board))
        self.assertFalse(get_is_moderator(mod_user, board))
        self.assertTrue(get_is_moderator(perms_user, board))
        self.assertTrue(get_is_moderator(owner_user, board))
        self.assertTrue(get_is_moderator(staff_user, board))

        board_mod = Board.objects.create(title="Test Board Mod", owner=owner_user)
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


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class TestImageUtils(TestCase):
    module_dir = os.path.dirname(__file__)
    image_path = os.path.join(module_dir, "images/white_horizontal.png")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_get_image_upload_path(self):
        board = Board.objects.create(title="Test Board")
        for type, _ in IMAGE_TYPE:
            with open(self.image_path, "rb") as image_file:
                img = Image(
                    type=type,
                    image=SimpleUploadedFile(
                        name=f"{type}.png",
                        content=image_file.read(),
                    ),
                    board=board if type == "p" else None,
                )
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
        exts = ["png", "jpg", "bmp", "gif"]
        for ext in exts:
            for type, _ in IMAGE_TYPE:
                for orientation in ["horizontal", "vertical"]:
                    image_path = os.path.join(self.module_dir, f"images/white_{orientation}.{ext}")
                    with open(image_path, "rb") as image_file:
                        img = Image(
                            image=SimpleUploadedFile(
                                name=f"{type}-{orientation}.{ext}",
                                content=image_file.read(),
                            )
                        )
                    img.image = process_image(img.image, type=type)

                    if type == "p":
                        max_width = settings.MAX_POST_IMAGE_WIDTH
                        max_height = settings.MAX_POST_IMAGE_HEIGHT
                    else:
                        max_width = settings.MAX_IMAGE_WIDTH
                        max_height = settings.MAX_IMAGE_HEIGHT

                    self.assertLessEqual(img.image.width, max_width)
                    self.assertLessEqual(img.image.height, max_height)

                    if ext not in ["jpg", "png"]:
                        pilimage = PILImage.open(img.image)
                        self.assertEqual(pilimage.format, "JPEG")
