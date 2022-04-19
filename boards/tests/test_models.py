import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.defaultfilters import date
from django.test import TestCase, override_settings

from boards.models import BACKGROUND_TYPE, IMAGE_TYPE, Board, BoardPreferences, Image, Post, Topic


class BoardModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        Board.objects.create(title="Test Board", description="Test Board Description", owner=test_user1)

    def test_title_max_length(self):
        board = Board.objects.get(title="Test Board")
        max_length = board._meta.get_field("title").max_length
        self.assertEqual(max_length, 50)

    def test_description_max_length(self):
        board = Board.objects.get(title="Test Board")
        max_length = board._meta.get_field("description").max_length
        self.assertEqual(max_length, 100)

    def test_object_name_is_title(self):
        board = Board.objects.get(title="Test Board")
        self.assertEqual(str(board), board.title)

    def test_slug_format(self):
        slug = Board.objects.get(title="Test Board").slug
        self.assertRegex(slug, r"^\d{6}$")

    def test_board_remain_after_user_delete(self):
        user = User.objects.get(username="testuser1")
        board_count_before = Board.objects.count()
        user.delete()
        board_count_after = Board.objects.count()
        self.assertEqual(board_count_before, board_count_after)
        self.assertIsNone(Board.objects.get(title="Test Board").owner)

    def test_get_post_count(self):
        board = Board.objects.get(title="Test Board")
        self.assertEqual(board.get_post_count, 0)
        self.assertEqual(board.get_post_count, Post.objects.filter(topic__board=board).count())
        topic = Topic.objects.create(board=board, subject="Test Topic")
        post = Post.objects.create(topic=topic, content="Test Post")
        board = Board.objects.get(title="Test Board")
        self.assertEqual(board.get_post_count, 1)
        self.assertEqual(board.get_post_count, Post.objects.filter(topic__board=board).count())

    def test_get_post_last_updated(self):
        board = Board.objects.get(title="Test Board")
        self.assertIsNone(board.get_last_post_date)
        topic = Topic.objects.create(board=board, subject="Test Topic")
        post1 = Post.objects.create(topic=topic, content="Test Post")
        post2 = Post.objects.create(topic=topic, content="Test Post 2")
        # make sure another board's posts are not counted
        board2 = Board.objects.create(title="Test Board 2", description="Test Board Description")
        topic2 = Topic.objects.create(board=board2, subject="Test Topic 2")
        post3 = Post.objects.create(topic=topic2, content="Test Post 3")
        board = Board.objects.get(title="Test Board")
        self.assertEqual(board.get_last_post_date, date(post2.created_at, "d/m/Y"))

    def test_get_absolute_url(self):
        board = Board.objects.get(title="Test Board")
        self.assertEqual(board.get_absolute_url(), f"/boards/{board.slug}/")


class BoardPreferencesModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        Board.objects.create(title="Test Board", description="Test Board Description", owner=test_user1)

    def test_board_has_preferences(self):
        board = Board.objects.get(title="Test Board")
        self.assertIsNotNone(board.preferences)

    def test_preferences_name(self):
        preferences = BoardPreferences.objects.get(board=Board.objects.get(title="Test Board"))
        self.assertEqual(str(preferences), "Test Board preferences")

    def test_get_absolute_url(self):
        preferences = BoardPreferences.objects.get(board=Board.objects.get(title="Test Board"))
        self.assertEqual(preferences.get_absolute_url(), f"/boards/{preferences.board.slug}/preferences/")

    def test_inverse_opacity(self):
        preferences = BoardPreferences.objects.get(board=Board.objects.get(title="Test Board"))
        self.assertEqual(preferences.get_inverse_opacity, 1.0 - preferences.background_opacity)

    def test_preferences_deleted_after_board_delete(self):
        board = Board.objects.get(title="Test Board")
        preferences = BoardPreferences.objects.get(board=board)
        board.delete()
        self.assertRaises(BoardPreferences.DoesNotExist, BoardPreferences.objects.get, id=preferences.id)


class TopicModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create two users
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board1 = Board.objects.create(title="Test Board", description="Test Board Description", owner=test_user1)
        Topic.objects.create(subject="Test Topic", board=board1)
        board2 = Board.objects.create(title="Test Board 2", description="Test Board 2 Description", owner=test_user2)
        Topic.objects.create(subject="Test Topic 2", board=board2)

    def test_subject_max_length(self):
        topic = Topic.objects.get(subject="Test Topic")
        max_length = topic._meta.get_field("subject").max_length
        self.assertEqual(max_length, 50)

    def test_object_name_is_subject(self):
        topic = Topic.objects.get(subject="Test Topic")
        self.assertEqual(str(topic), topic.subject)

    def test_get_board_name(self):
        topic = Topic.objects.get(subject="Test Topic")
        self.assertEqual(topic.get_board_name(), topic.board.title)

    def test_get_absolute_url(self):
        topic = Topic.objects.get(subject="Test Topic")
        self.assertEqual(topic.get_absolute_url(), f"/boards/{topic.board.slug}/")

    def test_topic_deleted_after_board_delete(self):
        board = Board.objects.get(title="Test Board")
        topic = Topic.objects.get(board=board)
        board.delete()
        self.assertRaises(Topic.DoesNotExist, Topic.objects.get, id=topic.id)


class PostModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create two users
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Board Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)
        Post.objects.create(content="Test Post", topic=topic)
        Post.objects.create(content="Test Post 2", topic=topic)

    def test_content_max_length(self):
        post = Post.objects.get(content="Test Post")
        max_length = post._meta.get_field("content").max_length
        self.assertEqual(max_length, 400)

    def test_object_name_is_content(self):
        post = post = Post.objects.get(content="Test Post")
        self.assertEqual(str(post), post.content)

    def test_get_absolute_url(self):
        post = post = Post.objects.get(content="Test Post")
        self.assertEqual(post.get_absolute_url(), f"/boards/{post.topic.board.slug}/")

    def test_post_deleted_after_topic_delete(self):
        topic = Topic.objects.get(subject="Test Topic")
        post = post = Post.objects.get(content="Test Post")
        topic.delete()
        self.assertRaises(Post.DoesNotExist, Post.objects.get, id=post.id)

    def test_post_deleted_after_board_delete(self):
        board = Board.objects.get(title="Test Board")
        post1 = post = Post.objects.get(content="Test Post")
        post2 = post = Post.objects.get(content="Test Post 2")
        board.delete()
        self.assertRaises(Post.DoesNotExist, Post.objects.get, id=post1.id)
        self.assertRaises(Post.DoesNotExist, Post.objects.get, id=post2.id)


MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ImageModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        module_dir = os.path.dirname(__file__)
        image_path = os.path.join(module_dir, "images/white.jpg")
        for type, text in IMAGE_TYPE:
            for orientation in ["horizontal", "vertical"]:
                image_path = os.path.join(module_dir, f"images/white_{orientation}.png")
                img = Image(
                    type=type,
                    image=SimpleUploadedFile(
                        name=f"{type}.png",
                        content=open(image_path, "rb").read(),
                        content_type="image/png",
                    ),
                    title=f"{text} - {orientation}",
                )
                img.save()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_image_name_is_title(self):
        for type, text in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                self.assertEqual(str(img), img.title)

    def test_image_url(self):
        for type, text in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                self.assertEqual(img.image.url, f"/media/images/{type}/{img.uuid}.png")

    def test_image_max_dimensions(self):
        for type, text in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                self.assertLessEqual(img.image.width, 3840)
                self.assertLessEqual(img.image.height, 2160)

    def test_get_board_usage_count(self):
        board = Board.objects.create(title="Test Board", description="Test Board Description")
        for type, text in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                board.preferences.background_image = img
                board.preferences.background_type = "i"
                board.preferences.save()
                if type == "b":
                    self.assertEqual(img.get_board_usage_count, 1)
                else:
                    self.assertEqual(img.get_board_usage_count, 0)

    def test_thumbnail_url_and_dimensions(self):

        for type, text in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                thumbnail = img.get_thumbnail()
                self.assertIsNotNone(thumbnail)
                self.assertEqual(thumbnail.width, 300)
                self.assertEqual(thumbnail.height, 200)
                self.assertIn("/media/cache/", thumbnail.url)

    def test_image_tag(self):
        for type, text in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                self.assertEqual(f'<img src="{img.get_thumbnail().url}" />', img.image_tag())
