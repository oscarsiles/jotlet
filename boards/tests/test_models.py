import os
import shutil
import tempfile
from datetime import timedelta

import factory
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.template.defaultfilters import date
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from PIL import Image as PILImage

from accounts.tests.factories import UserFactory
from boards.models import IMAGE_TYPE, BgImage, Board, BoardPreferences, Image, Post, PostImage, Reaction, Topic

from .factories import (
    BgImageFactory,
    BoardFactory,
    ImageFactory,
    PostFactory,
    PostImageFactory,
    ReactionFactory,
    TopicFactory,
)

MEDIA_ROOT = tempfile.mkdtemp()
IMAGE_EXTS = ["png", "jpg", "bmp", "gif"]
BASE_TEST_IMAGE_PATH = "images/white_"


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class BoardModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.board = BoardFactory()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_title_max_length(self):
        max_length = self.board._meta.get_field("title").max_length
        self.assertEqual(max_length, 50)

    def test_description_max_length(self):
        max_length = self.board._meta.get_field("description").max_length
        self.assertEqual(max_length, 100)

    def test_object_name_is_title(self):
        self.assertEqual(str(self.board), self.board.title)

    def test_slug_format(self):
        self.assertRegex(self.board.slug, r"^[a-z0-9]{8}$")  # make sure we are only generating the new type of slug

    def test_board_remain_after_user_delete(self):
        user = self.board.owner
        board_count_before = Board.objects.count()
        user.delete()
        board_count_after = Board.objects.count()
        self.assertEqual(board_count_before, board_count_after)
        self.assertIsNone(Board.objects.get(pk=self.board.pk).owner)

    def test_get_post_count(self):
        self.assertEqual(self.board.get_post_count, 0)
        self.assertEqual(self.board.get_post_count, Post.objects.filter(topic__board=self.board).count())
        topic = TopicFactory(board=self.board)
        PostFactory(topic=topic)
        self.board = Board.objects.get(pk=self.board.pk)
        self.assertEqual(self.board.get_post_count, 1)
        self.assertEqual(self.board.get_post_count, Post.objects.filter(topic__board=self.board).count())

    def test_get_last_post_date(self):
        self.assertIsNone(self.board.get_last_post_date)
        topic = TopicFactory(board=self.board)
        PostFactory(topic=topic, created_at=timezone.now() - timedelta(days=2))
        post2 = PostFactory(topic=topic, created_at=timezone.now() - timedelta(days=1))
        # make sure another board's posts are not counted
        board2 = BoardFactory()
        topic2 = TopicFactory(board=board2)
        PostFactory(topic=topic2)
        self.board = Board.objects.get(pk=self.board.pk)
        self.assertEqual(self.board.get_last_post_date, date(post2.created_at, "d/m/Y"))

    def test_get_postimage_count(self):
        self.assertEqual(self.board.get_postimage_count, 0)

        img_count1 = len(PostImageFactory.create_batch(3, board=self.board))
        img_count2 = len(BgImageFactory.create_batch(2))
        self.board = Board.objects.get(pk=self.board.pk)
        self.assertEqual(Image.objects.count(), img_count1 + img_count2)
        self.assertLess(self.board.get_postimage_count, img_count1 + img_count2)
        self.assertEqual(self.board.get_postimage_count, img_count1)

    def test_get_absolute_url(self):
        self.assertEqual(self.board.get_absolute_url(), f"/boards/{self.board.slug}/")


class BoardPreferencesModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.board = BoardFactory()

    def test_board_has_preferences(self):
        self.assertIsNotNone(self.board.preferences)

    def test_preferences_name(self):
        self.assertEqual(str(self.board.preferences), f"{self.board} preferences")

    def test_get_absolute_url(self):
        self.assertEqual(self.board.preferences.get_absolute_url(), f"/boards/{self.board.slug}/preferences/")

    def test_inverse_opacity(self):
        self.assertEqual(self.board.preferences.get_inverse_opacity, 1.0 - self.board.preferences.background_opacity)

    def test_preferences_deleted_after_board_delete(self):
        preferences_pk = self.board.preferences.pk
        self.board.delete()
        self.assertRaises(BoardPreferences.DoesNotExist, BoardPreferences.objects.get, pk=preferences_pk)


class TopicModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.topic = TopicFactory()

    def test_subject_max_length(self):
        self.assertEqual(self.topic._meta.get_field("subject").max_length, 400)

    def test_object_name_is_subject(self):
        self.assertEqual(str(self.topic), self.topic.subject)

    def test_get_board_name(self):
        self.assertEqual(self.topic.get_board_name(), self.topic.board.title)

    def test_get_last_post_date(self):
        self.assertIsNone(self.topic.get_last_post_date)
        post = PostFactory(topic=self.topic)
        self.topic = Topic.objects.get(pk=self.topic.pk)
        self.assertEqual(self.topic.get_last_post_date, date(post.created_at, "d/m/Y"))
        PostFactory(topic=self.topic, created_at=timezone.now() - timedelta(days=1))
        self.topic = Topic.objects.get(pk=self.topic.pk)
        self.assertEqual(self.topic.get_last_post_date, date(post.created_at, "d/m/Y"))

    def test_get_absolute_url(self):
        self.assertEqual(self.topic.get_absolute_url(), f"/boards/{self.topic.board.slug}/")

    def test_topic_deleted_after_board_delete(self):
        self.topic.board.delete()
        self.assertRaises(Topic.DoesNotExist, Topic.objects.get, pk=self.topic.pk)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PostModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.post = PostFactory()
        cls.post.topic.board.owner = cls.user
        cls.post.topic.board.save()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_content_max_length(self):
        self.assertEqual(self.post._meta.get_field("content").max_length, 1000)

    def test_object_name_is_content(self):
        self.assertEqual(str(self.post), self.post.content)

    def test_get_reaction_score_like(self):
        self.assertEqual(self.post.get_reaction_score(), 0)
        type = "l"
        self.post.topic.board.preferences.reaction_type = type
        self.post.topic.board.preferences.save()
        ReactionFactory.create_batch(2, post=self.post)
        self.post = Post.objects.get(pk=self.post.pk)
        self.assertEqual(self.post.get_reaction_score(), 2)

    def test_get_reaction_score_vote(self):
        self.assertEqual(self.post.get_reaction_score(), 0)
        type = "v"
        self.post.topic.board.preferences.reaction_type = type
        self.post.topic.board.preferences.save()
        ReactionFactory.reset_sequence(1)
        ReactionFactory.create_batch(
            4,
            post=self.post,
            type=type,
            reaction_score=factory.Sequence(lambda n: 1 if n % 2 == 0 else -1),  # 2 upvotes, 2 downvotes
        )
        self.post = Post.objects.get(pk=self.post.pk)
        self.assertEqual(self.post.get_reaction_score(), (2, 2))

    def test_get_reaction_score_star(self):
        self.assertEqual(self.post.get_reaction_score(), 0)
        type = "s"
        self.post.topic.board.preferences.reaction_type = type
        self.post.topic.board.preferences.save()
        ReactionFactory.reset_sequence(1)
        ReactionFactory.create_batch(
            4,
            post=self.post,
            type=type,
            reaction_score=factory.Sequence(lambda n: n),  # 1, 2, 3, 4
        )
        self.post = Post.objects.get(pk=self.post.pk)
        self.assertEqual(self.post.get_reaction_score(), f"{((1+2+3+4)/4):.2g}")

    def test_get_reaction_score_none(self):
        self.assertEqual(self.post.get_reaction_score(), 0)
        type = "n"
        self.post.topic.board.preferences.reaction_type = type
        self.post.topic.board.preferences.save()
        self.post = Post.objects.get(pk=self.post.pk)
        self.assertEqual(self.post.get_reaction_score(), 0)

    def test_get_reaction_score_unknown(self):
        self.assertEqual(self.post.get_reaction_score(), 0)
        type = "?"
        self.post.topic.board.preferences.reaction_type = type
        self.post.topic.board.preferences.save()
        self.post = Post.objects.get(pk=self.post.pk)
        self.assertEqual(self.post.get_reaction_score(), 0)

    def test_get_has_reacted(self):
        type = "l"
        self.post.topic.board.preferences.reaction_type = type
        self.post.topic.board.preferences.save()

        factory = RequestFactory()
        request = factory.post(
            reverse(
                "boards:post-reaction",
                kwargs={"slug": self.post.topic.board.slug, "topic_pk": self.post.topic_id, "pk": self.post.pk},
            )
        )
        session_middleware = SessionMiddleware(request)
        session_middleware.process_request(request)
        request.session.save()
        request.user = self.user

        ReactionFactory(post=self.post, reaction_score=1, session_key=request.session.session_key, user=self.user)
        has_reacted, reaction_id, reacted_score = self.post.get_has_reacted(request)
        self.assertTrue(has_reacted)
        self.assertEqual(reaction_id, Reaction.objects.get(post=self.post, user=self.user).pk)
        self.assertEqual(reacted_score, 1)

        Reaction.objects.filter(post=self.post, user=self.user).update(session_key="test")
        self.post = Post.objects.get(pk=self.post.pk)
        has_reacted, reaction_id, reacted_score = self.post.get_has_reacted(request)
        self.assertTrue(has_reacted)
        self.assertEqual(reaction_id, Reaction.objects.get(post=self.post, user=self.user).pk)
        self.assertEqual(reacted_score, 1)

    def test_get_absolute_url(self):
        self.assertEqual(self.post.get_absolute_url(), f"/boards/{self.post.topic.board.slug}/")

    def test_post_deleted_after_topic_delete(self):
        self.post.topic.delete()
        self.assertRaises(Post.DoesNotExist, Post.objects.get, pk=self.post.pk)

    def test_post_deleted_after_board_delete(self):
        post2 = PostFactory(topic=self.post.topic)
        self.post.topic.board.delete()
        self.assertRaises(Post.DoesNotExist, Post.objects.get, pk=self.post.pk)
        self.assertRaises(Post.DoesNotExist, Post.objects.get, pk=post2.pk)

    def test_cleanup_image_uploads(self):
        self.post.topic.board.preferences.allow_image_uploads = True
        self.post.topic.board.preferences.save()

        post_image1, post_image2 = PostImageFactory.create_batch(2, board=self.post.topic.board)
        self.assertEqual(PostImage.objects.count(), 2)

        # test on create
        post = PostFactory(content=f"<img src='{post_image1.image.url}'/>", topic=self.post.topic)
        post_image1 = PostImage.objects.get(pk=post_image1.pk)
        self.assertEqual(post_image1.post, post)

        # test after update
        post = Post.objects.get(pk=self.post.pk)
        post.content = f"<img src='{post_image2.image.url}'/>"
        post.save()
        post_image2 = PostImage.objects.get(pk=post_image2.pk)
        self.assertEqual(post_image2.post, post)


# TODO: Reaction model tests
class ReactionModelTest(TestCase):
    pass


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ImageModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.board = BoardFactory()
        for ext in IMAGE_EXTS:
            for type, text in IMAGE_TYPE:
                ImageFactory(board=cls.board if type == "p" else None, type=type)

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
        board = BoardFactory()
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

    def test_get_image_dimensions(self):
        imgs = Image.objects.all()
        for img in imgs:
            self.assertEqual(img.get_image_dimensions, f"{img.image.width}x{img.image.height}")

    def test_get_half_image_dimensions(self):
        imgs = Image.objects.all()
        for img in imgs:
            self.assertEqual(img.get_half_image_dimensions, f"{img.image.width // 2}x{img.image.height // 2}")

    def test_get_small_thumbnail_dimensions(self):
        self.assertEqual(
            Image.objects.first().get_small_thumbnail_dimensions,
            f"{settings.SMALL_THUMBNAIL_WIDTH}x{settings.SMALL_THUMBNAIL_HEIGHT}",
        )

    def test_get_webp(self):
        imgs = Image.objects.all()
        for img in imgs:
            pilimage = PILImage.open(img.get_webp)
            self.assertEqual(pilimage.format, "WEBP")

    def test_thumbnail_url_and_dimensions(self):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                small_thumb = img.get_small_thumbnail
                large_thumb = img.get_large_thumbnail
                thumbs = [small_thumb, large_thumb]
                for thumb in thumbs:
                    self.assertIsNotNone(thumb)
                    self.assertIn(f"{settings.MEDIA_URL}cache/", thumb.url)
                    self.assertTrue(os.path.exists(f"{settings.MEDIA_ROOT}/{thumb.name}"))
                    for res in settings.THUMBNAIL_ALTERNATIVE_RESOLUTIONS:
                        name, ext = os.path.splitext(thumb.name)
                        self.assertTrue(os.path.exists(f"{settings.MEDIA_ROOT}/{name}@{res}x{ext}"))

                self.assertLessEqual(small_thumb.width, settings.SMALL_THUMBNAIL_WIDTH)
                self.assertLessEqual(small_thumb.height, settings.SMALL_THUMBNAIL_HEIGHT)
                self.assertLessEqual(large_thumb.width, img.image.width / 2)
                self.assertLessEqual(large_thumb.height, img.image.height / 2)

    def test_image_tag(self):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                self.assertEqual(f'<img src="{escape(img.get_small_thumbnail.url)}" />', img.image_tag)

    def test_proxy_background_image(self):
        self.assertEqual(list(Image.objects.filter(type="b")), list(BgImage.objects.all()))

        count_before = BgImage.objects.count()
        BgImageFactory()
        self.assertEqual(BgImage.objects.count(), count_before + 1)

    def test_proxy_post_image(self):
        self.assertEqual(list(Image.objects.filter(type="p")), list(PostImage.objects.all()))

        count_before = PostImage.objects.count()
        PostImageFactory()
        self.assertEqual(PostImage.objects.count(), count_before + 1)
