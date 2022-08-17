import os
import shutil
import tempfile
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.defaultfilters import date
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils.html import escape
from PIL import Image as PILImage

from boards.models import IMAGE_TYPE, BgImage, Board, BoardPreferences, Image, Post, PostImage, Reaction, Topic

MEDIA_ROOT = tempfile.mkdtemp()
IMAGE_EXTS = ["png", "jpg", "bmp", "gif"]
BASE_TEST_IMAGE_PATH = "images/white_"


def create_image(file, name, type, board=None, title="test"):
    module_dir = os.path.dirname(__file__)
    image_path = os.path.join(module_dir, file)
    with open(image_path, "rb") as image_file:
        image = Image.objects.create(
            type=type,
            image=SimpleUploadedFile(
                name=name,
                content=image_file.read(),
            ),
            board=board,
            title=title,
        )
    return image


def create_images(board=None):
    if board is None:
        board = Board.objects.create(title="Test Board")
    count = 0
    for ext in IMAGE_EXTS:
        for type, text in IMAGE_TYPE:
            for orientation in ["horizontal", "vertical"]:
                create_image(
                    f"{BASE_TEST_IMAGE_PATH}{orientation}.{ext}",
                    f"{type}.{ext}",
                    type,
                    board=board if type == "p" else None,
                    title=f"{type}_{text}_{orientation}_{ext}",
                )
                count += 1
    return count


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class BoardModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        Board.objects.create(title="Test Board", description="Test Board Description", owner=test_user1)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

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
        self.assertRegex(slug, r"^[a-z0-9]{8}$")  # make sure we are only generating the new type of slug

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
        Post.objects.create(topic=topic, content="Test Post")
        board = Board.objects.get(title="Test Board")
        self.assertEqual(board.get_post_count, 1)
        self.assertEqual(board.get_post_count, Post.objects.filter(topic__board=board).count())

    def test_get_last_post_date(self):
        board = Board.objects.get(title="Test Board")
        self.assertIsNone(board.get_last_post_date)
        topic = Topic.objects.create(board=board, subject="Test Topic")
        Post.objects.create(topic=topic, content="Test Post", created_at=datetime.now() - timedelta(days=2))
        post2 = Post.objects.create(topic=topic, content="Test Post 2", created_at=datetime.now() - timedelta(days=1))
        # make sure another board's posts are not counted
        board2 = Board.objects.create(title="Test Board 2", description="Test Board Description")
        topic2 = Topic.objects.create(board=board2, subject="Test Topic 2")
        Post.objects.create(topic=topic2, content="Test Post 3")
        board = Board.objects.get(title="Test Board")
        self.assertEqual(board.get_last_post_date, date(post2.created_at, "d/m/Y"))

    def test_get_image_count(self):
        board = Board.objects.get(title="Test Board")
        self.assertEqual(board.get_image_count, 0)

        img_count1 = create_images(board)
        img_count2 = create_images(Board.objects.create(title="Test Board 2"))
        board = Board.objects.get(title="Test Board")
        self.assertEqual(Image.objects.count(), img_count1 + img_count2)
        self.assertLess(board.get_image_count, img_count1)
        self.assertEqual(board.get_image_count, len(IMAGE_EXTS) * 2)  # extensions * orientations

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
        self.assertEqual(max_length, 400)

    def test_object_name_is_subject(self):
        topic = Topic.objects.get(subject="Test Topic")
        self.assertEqual(str(topic), topic.subject)

    def test_get_board_name(self):
        topic = Topic.objects.get(subject="Test Topic")
        self.assertEqual(topic.get_board_name(), topic.board.title)

    def test_get_last_post_date(self):
        topic = Topic.objects.get(subject="Test Topic")
        self.assertIsNone(topic.get_last_post_date)
        Post.objects.create(topic=topic, content="Test Post", created_at=datetime.today() - timedelta(days=1))
        post2 = Post.objects.create(topic=topic, content="Test Post 2")
        topic = Topic.objects.get(subject="Test Topic")
        self.assertEqual(topic.get_last_post_date, date(post2.created_at, "d/m/Y"))

    def test_get_absolute_url(self):
        topic = Topic.objects.get(subject="Test Topic")
        self.assertEqual(topic.get_absolute_url(), f"/boards/{topic.board.slug}/")

    def test_topic_deleted_after_board_delete(self):
        board = Board.objects.get(title="Test Board")
        topic = Topic.objects.get(board=board)
        board.delete()
        self.assertRaises(Topic.DoesNotExist, Topic.objects.get, id=topic.id)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PostModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create two users
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Board Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)
        Post.objects.create(content="Test Post", topic=topic)
        Post.objects.create(content="Test Post 2", topic=topic)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_content_max_length(self):
        post = Post.objects.get(content="Test Post")
        max_length = post._meta.get_field("content").max_length
        self.assertEqual(max_length, 1000)

    def test_object_name_is_content(self):
        post = Post.objects.get(content="Test Post")
        self.assertEqual(str(post), post.content)

    def test_get_reaction_score(self):
        post = Post.objects.get(content="Test Post")
        self.assertEqual(post.get_reaction_score(), 0)

        # like
        type = "l"
        post.topic.board.preferences.reaction_type = type
        post.topic.board.preferences.save()
        Reaction.objects.create(post=post, reaction_score=1, session_key="test1")
        Reaction.objects.create(post=post, reaction_score=1, session_key="test2")
        post = Post.objects.get(content="Test Post")  # post has cached property
        self.assertEqual(post.get_reaction_score(), 2)

        # vote
        type = "v"
        post.topic.board.preferences.reaction_type = type
        post.topic.board.preferences.save()
        Reaction.objects.create(post=post, reaction_score=1, type=type, session_key="test1")
        Reaction.objects.create(post=post, reaction_score=1, type=type, session_key="test2")
        Reaction.objects.create(post=post, reaction_score=-1, type=type, session_key="test3")
        Reaction.objects.create(post=post, reaction_score=-1, type=type, session_key="test4")
        post = Post.objects.get(content="Test Post")
        self.assertEqual(post.get_reaction_score(), (2, 2))

        # star
        type = "s"
        post.topic.board.preferences.reaction_type = type
        post.topic.board.preferences.save()
        Reaction.objects.create(post=post, reaction_score=1, type=type, session_key="test1")
        Reaction.objects.create(post=post, reaction_score=2, type=type, session_key="test2")
        Reaction.objects.create(post=post, reaction_score=3, type=type, session_key="test3")
        Reaction.objects.create(post=post, reaction_score=4, type=type, session_key="test4")
        post = Post.objects.get(content="Test Post")
        self.assertEqual(post.get_reaction_score(), f"{((1+2+3+4)/4):.2g}")

        # none
        type = "n"
        post.topic.board.preferences.reaction_type = type
        post.topic.board.preferences.save()
        post = Post.objects.get(content="Test Post")
        self.assertEqual(post.get_reaction_score(), 0)

        # unknown
        type = "?"
        post.topic.board.preferences.reaction_type = type
        post.topic.board.preferences.save()
        post = Post.objects.get(content="Test Post")
        self.assertEqual(post.get_reaction_score(), 0)

    def test_get_has_reacted(self):
        type = "l"
        post = Post.objects.get(content="Test Post")
        post.topic.board.preferences.reaction_type = type
        post.topic.board.preferences.save()
        user = User.objects.get(username="testuser1")

        factory = RequestFactory()
        request = factory.post(
            reverse(
                "boards:post-reaction",
                kwargs={"slug": post.topic.board.slug, "topic_pk": post.topic_id, "pk": post.pk},
            )
        )
        session_middleware = SessionMiddleware(request)
        session_middleware.process_request(request)
        request.session.save()
        request.user = user

        Reaction.objects.create(post=post, reaction_score=1, session_key=request.session.session_key, user=user)
        has_reacted, reaction_id, reacted_score = post.get_has_reacted(request)
        self.assertTrue(has_reacted)
        self.assertEqual(reaction_id, Reaction.objects.get(post=post, user=user).pk)
        self.assertEqual(reacted_score, 1)

        Reaction.objects.filter(post=post, user=user).update(session_key="test")
        post = Post.objects.get(content="Test Post")
        has_reacted, reaction_id, reacted_score = post.get_has_reacted(request)
        self.assertTrue(has_reacted)
        self.assertEqual(reaction_id, Reaction.objects.get(post=post, user=user).pk)
        self.assertEqual(reacted_score, 1)

    def test_get_absolute_url(self):
        post = Post.objects.get(content="Test Post")
        self.assertEqual(post.get_absolute_url(), f"/boards/{post.topic.board.slug}/")

    def test_post_deleted_after_topic_delete(self):
        topic = Topic.objects.get(subject="Test Topic")
        post = Post.objects.get(content="Test Post")
        topic.delete()
        self.assertRaises(Post.DoesNotExist, Post.objects.get, id=post.id)

    def test_post_deleted_after_board_delete(self):
        board = Board.objects.get(title="Test Board")
        post1 = Post.objects.get(content="Test Post")
        post2 = Post.objects.get(content="Test Post 2")
        board.delete()
        self.assertRaises(Post.DoesNotExist, Post.objects.get, id=post1.id)
        self.assertRaises(Post.DoesNotExist, Post.objects.get, id=post2.id)

    def test_cleanup_image_uploads(self):
        topic = Topic.objects.get(subject="Test Topic")
        board = Board.objects.get(title="Test Board")
        board.preferences.allow_image_uploads = True
        board.preferences.save()

        for i in range(2):
            create_image(
                f"{BASE_TEST_IMAGE_PATH}horizontal.png",
                "test.png",
                type="p",
                board=board,
                title=f"Test Post Image {i}",
            )
        self.assertEqual(PostImage.objects.count(), 2)

        # test on create
        post_image1 = PostImage.objects.get(title="Test Post Image 0")
        post = Post.objects.create(content=f"<img src='{post_image1.image.url}'/>", topic=topic)
        post_image1 = PostImage.objects.get(title="Test Post Image 0")
        self.assertEqual(post_image1.post, post)

        # test after update
        post_image2 = PostImage.objects.get(title="Test Post Image 1")
        post = Post.objects.get(content="Test Post")
        post.content = f"<img src='{post_image2.image.url}'/>"
        post.save()
        post_image2 = PostImage.objects.get(title="Test Post Image 1")
        self.assertEqual(post_image2.post, post)


class ReactionModelTest(TestCase):
    pass


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ImageModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        board = Board.objects.create(title="Test Board")
        create_images(board)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_image_name_is_title(self):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                self.assertEqual(str(img), img.title)

    def test_image_url(self):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                _, ext = os.path.splitext(img.image.name)
                self.assertRegex(
                    img.image.url, rf"^{settings.MEDIA_URL}images/{type}/[a-z0-9]+/[a-z0-9]{{2}}/{img.uuid}{ext}$"
                )

    def test_image_max_dimensions(self):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                if img.type == "p":
                    self.assertLessEqual(img.image.width, settings.MAX_POST_IMAGE_WIDTH)
                    self.assertLessEqual(img.image.height, settings.MAX_POST_IMAGE_HEIGHT)
                else:
                    self.assertLessEqual(img.image.width, settings.MAX_IMAGE_WIDTH)
                    self.assertLessEqual(img.image.height, settings.MAX_IMAGE_HEIGHT)

    def test_get_board_usage_count(self):
        board = Board.objects.create(title="Test Board", description="Test Board Description")
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                board.preferences.background_image = img
                board.preferences.background_type = "i"
                board.preferences.save()
                if type == "b":
                    self.assertEqual(img.get_board_usage_count, 1)
                else:
                    self.assertEqual(img.get_board_usage_count, 0)

    def test_get_image_dimenstions(self):
        imgs = Image.objects.all()
        for img in imgs:
            self.assertEqual(img.get_image_dimensions, f"{img.image.width}x{img.image.height}")

    def test_get_webp(self):
        imgs = Image.objects.all()
        for img in imgs:
            pilimage = PILImage.open(img.get_webp)
            self.assertEqual(pilimage.format, "WEBP")

    def test_thumbnail_url_and_dimensions(self):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                thumbnail = img.get_thumbnail
                self.assertIsNotNone(thumbnail)
                self.assertEqual(thumbnail.width, 300)
                self.assertEqual(thumbnail.height, 200)
                self.assertIn(f"{settings.MEDIA_URL}cache/", thumbnail.url)

    def test_image_tag(self):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                self.assertEqual(f'<img src="{escape(img.get_thumbnail.url)}" />', img.image_tag)

    def test_proxy_background_image(self):
        self.assertEqual(list(Image.objects.filter(type="b")), list(BgImage.objects.all()))

    def test_proxy_post_image(self):
        self.assertEqual(list(Image.objects.filter(type="p")), list(PostImage.objects.all()))

        count_before = PostImage.objects.count()
        module_dir = os.path.dirname(__file__)
        image_path = os.path.join(module_dir, f"{BASE_TEST_IMAGE_PATH}horizontal.png")
        with open(image_path, "rb") as image_file:
            PostImage.objects.create(
                image=SimpleUploadedFile(name="test.png", content=image_file.read()),
                board=Board.objects.first(),
                title="test",
            )
        self.assertEqual(PostImage.objects.count(), count_before + 1)
