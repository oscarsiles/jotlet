import datetime
import os
import re
import shutil

import factory
import pytest
from django.conf import settings
from django.core.files.storage import default_storage
from django.template.defaultfilters import date
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from PIL import Image as PILImage

from boards.models import IMAGE_TYPE, BgImage, Board, BoardPreferences, Image, Post, PostImage, Reaction, Topic
from jotlet.tests.utils import create_session

IMAGE_FORMATS = ["png", "jpeg", "bmp", "gif"]


class TestBoardModel:
    @classmethod
    def teardown_class(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_title_max_length(self, board):
        max_length = board._meta.get_field("title").max_length
        assert max_length == 50

    def test_description_max_length(self, board):
        max_length = board._meta.get_field("description").max_length
        assert max_length == 100

    def test_object_name_is_title(self, board):
        assert str(board) == board.title

    def test_slug_format(self):
        for i in range(10):
            board = Board.objects.create(title=f"Board {i}", description="test")
            assert re.compile(r"^[a-z0-9]{8}$").search(
                board.slug
            )  # make sure we are only generating the new type of slug

    def test_board_deleted_after_user_delete(self, board, board_factory):
        owner_username = board.owner.username
        board_factory(owner=board.owner)
        board_factory()
        assert Board.objects.count() == 3
        assert Board.objects.filter(owner__username=owner_username).count() == 2
        board.owner.delete()
        assert Board.objects.filter(owner__username=owner_username).count() == 0

    def test_get_post_count(self, board, topic_factory, post_factory):
        assert board.get_post_count == 0
        assert board.get_post_count == Post.objects.filter(topic__board=board).count()
        topic = topic_factory(board=board)
        post_factory(topic=topic)
        board.refresh_from_db()
        assert board.get_post_count == 1
        assert board.get_post_count == Post.objects.filter(topic__board=board).count()

    def test_get_last_post_date(self, board, board_factory, topic_factory, post_factory):
        assert board.get_last_post_date is None
        topic = topic_factory(board=board)
        post_factory(topic=topic, created_at=timezone.now() - datetime.timedelta(days=2))
        post2 = post_factory(topic=topic, created_at=timezone.now() - datetime.timedelta(days=1))
        # make sure another board's posts are not counted
        board2 = board_factory()
        topic2 = topic_factory(board=board2)
        post_factory(topic=topic2)
        board.refresh_from_db()
        assert board.get_last_post_date == date(post2.created_at, "d/m/Y")

    def test_get_postimage_count(self, board, bg_image_factory, post_image_factory):
        assert board.get_postimage_count == 0

        img_count1 = len(post_image_factory.create_batch(3, board=board))
        img_count2 = len(bg_image_factory.create_batch(2))
        board.refresh_from_db()
        assert Image.objects.count() == img_count1 + img_count2
        assert board.get_postimage_count < img_count1 + img_count2
        assert board.get_postimage_count == img_count1

    def test_get_absolute_url(self, board):
        assert board.get_absolute_url() == f"/boards/{board.slug}/"

    @pytest.mark.parametrize("locked", [True, False])
    @pytest.mark.parametrize(
        "allowed_from,allowed_until,time_allowed",
        [
            (timezone.now() - datetime.timedelta(days=1), None, True),
            (None, timezone.now() + datetime.timedelta(days=1), True),
            (timezone.now() - datetime.timedelta(days=1), timezone.now() + datetime.timedelta(days=1), True),
            (timezone.now() - datetime.timedelta(days=1), timezone.now() - datetime.timedelta(days=2), True),
            (timezone.now() + datetime.timedelta(days=2), timezone.now() + datetime.timedelta(days=1), True),
            (timezone.now() + datetime.timedelta(days=1), timezone.now() + datetime.timedelta(days=2), False),
            (timezone.now() + datetime.timedelta(days=1), timezone.now() - datetime.timedelta(days=1), False),
        ],
    )
    def test_is_posting_allowed(self, board, locked, allowed_from, allowed_until, time_allowed):
        board.locked = locked
        board.save()
        board.preferences.posting_allowed_from = allowed_from
        board.preferences.posting_allowed_until = allowed_until
        board.preferences.save()
        assert board.is_posting_allowed == (time_allowed and not locked)


class TestBoardPreferencesModel:
    def test_board_has_preferences(self, board):
        assert board.preferences is not None

    def test_preferences_name(self, board):
        assert str(board.preferences) == f"{board} preferences"

    def test_get_absolute_url(self, board):
        assert board.preferences.get_absolute_url() == f"/boards/{board.slug}/preferences/"

    def test_inverse_opacity(self, board):
        assert board.preferences.get_inverse_opacity == 1.0 - board.preferences.background_opacity

    def test_preferences_deleted_after_board_delete(self, board):
        preferences_pk = board.preferences.pk
        board.delete()
        pytest.raises(BoardPreferences.DoesNotExist, BoardPreferences.objects.get, pk=preferences_pk)


class TestTopicModel:
    def test_subject_max_length(self, topic):
        assert topic._meta.get_field("subject").max_length == 400

    def test_object_name_is_subject(self, topic):
        assert str(topic) == topic.subject

    def test_get_topic_posts(self, topic, post_factory):
        post = post_factory(topic=topic)
        post_factory(topic=topic, parent=post)
        assert list(topic.get_posts) == list(Post.objects.filter(topic=topic, parent=None))

    def test_get_post_count(self, topic, post_factory):
        post1 = post_factory(topic=topic)
        post2 = post_factory(topic=topic)
        post_factory.create_batch(3, topic=topic, parent=post1)
        post_factory.create_batch(3, topic=topic, parent=post2)
        assert topic.get_post_count == 8

    def test_get_last_post_date(self, topic, post_factory):
        assert topic.get_last_post_date is None
        post = post_factory(topic=topic)
        topic.refresh_from_db()
        assert topic.get_last_post_date == date(post.created_at, "d/m/Y")
        post_factory(topic=topic, created_at=timezone.now() - datetime.timedelta(days=1))
        topic.refresh_from_db()
        assert topic.get_last_post_date == date(post.created_at, "d/m/Y")

    def test_get_absolute_url(self, topic):
        assert topic.get_absolute_url() == f"/boards/{topic.board.slug}/"

    def test_topic_deleted_after_board_delete(self, topic):
        topic.board.delete()
        pytest.raises(Topic.DoesNotExist, Topic.objects.get, pk=topic.pk)


class TestPostModel:
    @classmethod
    def teardown_class(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_content_max_length(self, post):
        assert post._meta.get_field("content").max_length == 1000

    def test_object_name_is_content(self, post):
        assert str(post) == post.content

    def test_get_descendant_count(self, post, post_factory):
        post_factory.create_batch(5, topic=post.topic, parent=post)
        assert post.get_descendant_count == 5

        post2 = post_factory(topic=post.topic, parent=post)
        post_factory.create_batch(5, topic=post.topic, parent=post2)
        post.refresh_from_db()
        assert post.get_descendant_count == 11

    def test_get_reaction_score_like(self, post, reaction_factory):
        assert post.get_reaction_score() == 0
        type = "l"
        post.topic.board.preferences.reaction_type = type
        post.topic.board.preferences.save()
        reaction_factory.create_batch(2, post=post)
        post.refresh_from_db()
        assert post.get_reaction_score() == 2

    def test_get_reaction_score_vote(self, post, reaction_factory):
        assert post.get_reaction_score() == 0
        type = "v"
        post.topic.board.preferences.reaction_type = type
        post.topic.board.preferences.save()
        reaction_factory.reset_sequence(1)
        reaction_factory.create_batch(
            4,
            post=post,
            type=type,
            reaction_score=factory.Sequence(lambda n: 1 if n % 2 == 0 else -1),  # 2 upvotes, 2 downvotes
        )
        post.refresh_from_db()
        assert post.get_reaction_score() == (2, 2)

    def test_get_reaction_score_star(self, post, reaction_factory):
        assert post.get_reaction_score() == 0
        type = "s"
        post.topic.board.preferences.reaction_type = type
        post.topic.board.preferences.save()
        reaction_factory.reset_sequence(1)
        reaction_factory.create_batch(
            4,
            post=post,
            type=type,
            reaction_score=factory.Sequence(lambda n: n),  # 1, 2, 3, 4
        )
        post.refresh_from_db()
        assert post.get_reaction_score() == f"{((1+2+3+4)/4):.2g}"

    def test_get_reaction_score_none(self, post):
        assert post.get_reaction_score() == 0
        type = "n"
        post.topic.board.preferences.reaction_type = type
        post.topic.board.preferences.save()
        post.refresh_from_db()
        assert post.get_reaction_score() == 0

    def test_get_reaction_score_unknown(self, post):
        assert post.get_reaction_score() == 0
        type = "?"
        post.topic.board.preferences.reaction_type = type
        post.topic.board.preferences.save()
        post.refresh_from_db()
        assert post.get_reaction_score() == 0

    def test_get_has_reacted(self, rf, post, user, reaction_factory):
        type = "l"
        post.topic.board.preferences.reaction_type = type
        post.topic.board.preferences.save()

        request = rf.post(
            reverse(
                "boards:post-reaction",
                kwargs={"slug": post.topic.board.slug, "topic_pk": post.topic_id, "pk": post.pk},
            )
        )
        create_session(request)
        request.user = user

        reaction_factory(post=post, reaction_score=1, session_key=request.session.session_key, user=user)
        has_reacted, reaction_id, reacted_score = post.get_has_reacted(request)
        assert has_reacted
        assert reaction_id == Reaction.objects.get(post=post, user=user).pk
        assert reacted_score == 1

        Reaction.objects.filter(post=post, user=user).invalidated_update(session_key="test")
        post.refresh_from_db()
        has_reacted, reaction_id, reacted_score = post.get_has_reacted(request)
        assert has_reacted
        assert reaction_id == Reaction.objects.get(post=post, user=user).pk
        assert reacted_score == 1

    def test_get_absolute_url(self, post):
        assert post.get_absolute_url() == f"/boards/{post.topic.board.slug}/"

    def test_post_deleted_after_topic_delete(self, post):
        post.topic.delete()
        pytest.raises(Post.DoesNotExist, Post.objects.get, pk=post.pk)

    def test_post_deleted_after_board_delete(self, post, post_factory):
        post2 = post_factory(topic=post.topic)
        post.topic.board.delete()
        pytest.raises(Post.DoesNotExist, Post.objects.get, pk=post.pk)
        pytest.raises(Post.DoesNotExist, Post.objects.get, pk=post2.pk)

    def test_cleanup_image_uploads(self, topic, post_factory, post_image_factory):
        topic.board.preferences.allow_image_uploads = True
        topic.board.preferences.save()

        post_image1, post_image2 = post_image_factory.create_batch(2, board=topic.board)
        assert PostImage.objects.count() == 2
        assert post_image1.post is None
        assert post_image2.post is None

        # test on create
        post = post_factory(content=f"<img src='{post_image1.image.url}'/>", topic=topic)
        post_image1.refresh_from_db()
        assert post_image1.post == post

        # test after update
        post.content = f"<img src='{post_image2.image.url}'/>"
        post.save()
        post_image2.refresh_from_db()
        assert post_image2.post == post


class TestReactionModel:
    def test_post_deleted_after_topic_delete(self, reaction):
        reaction.post.topic.delete()
        pytest.raises(Reaction.DoesNotExist, Reaction.objects.get, pk=reaction.pk)

    def test_post_deleted_after_board_delete(self, reaction, topic_factory, post_factory, reaction_factory):
        topic2 = topic_factory(board=reaction.post.topic.board)
        post2 = post_factory(topic=topic2)
        reaction2 = reaction_factory(post=post2)
        reaction.post.topic.board.delete()
        pytest.raises(Reaction.DoesNotExist, Reaction.objects.get, pk=reaction.pk)
        pytest.raises(Reaction.DoesNotExist, Reaction.objects.get, pk=reaction2.pk)


class TestImageModel:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, board, image_factory):
        for format in IMAGE_FORMATS:
            for type, _ in IMAGE_TYPE:
                image_factory(
                    board=board if type == "p" else None,
                    type=type,
                    image__format=format,
                    image__filename=f"test.{format}",
                )

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_image_name_is_title(self):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                assert str(img) == img.title

    def test_image_url(self):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                _, ext = os.path.splitext(img.image.name)
                assert re.compile(
                    rf"^{settings.MEDIA_URL}images/{type}/[a-z0-9]+/[a-z0-9]{{2}}/{img.id}{ext}$"
                ).search(img.image.url)

    def test_image_max_dimensions(self):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                if img.type == "p":
                    assert img.image.width <= settings.MAX_POST_IMAGE_WIDTH
                    assert img.image.height <= settings.MAX_POST_IMAGE_HEIGHT
                else:
                    assert img.image.width <= settings.MAX_IMAGE_WIDTH
                    assert img.image.height <= settings.MAX_IMAGE_HEIGHT

    def test_get_board_usage_count(self, board):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                board.preferences.background_image = img
                board.preferences.background_type = "i"
                board.preferences.save()
                if type == "b":
                    assert img.get_board_usage_count == 1
                else:
                    assert img.get_board_usage_count == 0

    def test_get_image_dimensions(self):
        imgs = Image.objects.all()
        for img in imgs:
            assert img.get_image_dimensions == f"{img.image.width}x{img.image.height}"

    def test_get_half_image_dimensions(self):
        imgs = Image.objects.all()
        for img in imgs:
            assert img.get_half_image_dimensions == f"{img.image.width // 2}x{img.image.height // 2}"

    def test_get_small_thumbnail_dimensions(self):
        assert (
            Image.objects.first().get_small_thumbnail_dimensions
            == f"{settings.SMALL_THUMBNAIL_WIDTH}x{settings.SMALL_THUMBNAIL_HEIGHT}"
        )

    def test_get_webp(self):
        imgs = Image.objects.all()
        for img in imgs:
            pilimage = PILImage.open(img.get_webp)
            assert pilimage.format == "WEBP"

    def test_thumbnail_url_and_dimensions(self):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                small_thumb = img.get_small_thumbnail
                large_thumb = img.get_large_thumbnail
                thumbs = [small_thumb, large_thumb]
                for thumb in thumbs:
                    assert thumb is not None
                    assert f"{settings.MEDIA_URL}cache/" in thumb.url
                    assert default_storage.exists(f"{settings.MEDIA_ROOT}{thumb.name}")
                    for res in settings.THUMBNAIL_ALTERNATIVE_RESOLUTIONS:
                        name, ext = os.path.splitext(thumb.name)
                        assert default_storage.exists(f"{settings.MEDIA_ROOT}/{name}@{res}x{ext}")

                assert small_thumb.width <= settings.SMALL_THUMBNAIL_WIDTH
                assert small_thumb.height <= settings.SMALL_THUMBNAIL_HEIGHT
                assert large_thumb.width <= img.image.width / 2
                assert large_thumb.height <= img.image.height / 2

    def test_image_tag(self):
        for type, _ in IMAGE_TYPE:
            imgs = Image.objects.filter(type=type)
            for img in imgs:
                assert f'<img src="{escape(img.get_small_thumbnail.url)}" />' == img.image_tag

    def test_proxy_background_image(self, bg_image_factory):
        assert list(Image.objects.filter(type="b")) == list(BgImage.objects.all())

        count_before = BgImage.objects.count()
        bg_image_factory()
        assert BgImage.objects.count() == count_before + 1

    def test_proxy_post_image(self, post_image_factory):
        assert list(Image.objects.filter(type="p")) == list(PostImage.objects.all())

        count_before = PostImage.objects.count()
        post_image_factory()
        assert PostImage.objects.count() == count_before + 1
