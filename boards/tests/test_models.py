import csv
import re
from io import StringIO
from pathlib import Path

import factory
import pytest
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import IntegrityError
from django.template.defaultfilters import date
from django.urls import reverse
from django.utils.html import escape
from freezegun import freeze_time
from PIL import Image as PILImage
from pytest_lazy_fixtures import lf

from boards.models import (
    ADDITIONAL_DATA_TYPE,
    IMAGE_FORMATS,
    IMAGE_TYPE,
    AdditionalData,
    BgImage,
    Board,
    BoardPreferences,
    Export,
    Image,
    Post,
    PostImage,
    Reaction,
    Topic,
)
from jotlet.tests.utils import create_session
from jotlet.utils import offset_date

ADDITIONAL_DATA_TYPE_CHOICES = [choice[0] for choice in ADDITIONAL_DATA_TYPE]


class TestBoardModel:
    def test_object_name_is_title(self, board):
        assert str(board) == board.title

    def test_slug_format(self, board_factory):
        board_factory.create_batch(10)
        slugs = Board.objects.values_list("slug", flat=True)

        assert all(re.match(r"^[a-z0-9]{8}$", slug) for slug in slugs)

    def test_board_deleted_after_user_delete(self, board, board_factory):
        owner_username = board.owner.username
        board_factory(owner=board.owner)  # 2
        board_factory()  # 3
        assert Board.objects.count() == 3  # noqa: PLR2004
        assert Board.objects.filter(owner__username=owner_username).count() == 2  # noqa: PLR2004
        board.owner.delete()
        assert Board.objects.filter(owner__username=owner_username).count() == 0
        assert Board.objects.count() == 1

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
        with freeze_time(offset_date(days=-2)):
            post_factory(topic=topic)
        with freeze_time(offset_date(days=-1)):
            post2 = post_factory(topic=topic)
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

    def test_is_additional_data_allowed(self, board):
        assert board.is_additional_data_allowed is False
        board.preferences.enable_chemdoodle = True
        board.preferences.save()
        board.refresh_from_db()
        assert board.is_additional_data_allowed is True

    def test_get_absolute_url(self, board):
        assert board.get_absolute_url() == f"/boards/{board.slug}/"

    @pytest.mark.parametrize("locked", [True, False])
    @pytest.mark.parametrize(
        ("allowed_from", "allowed_until", "is_time_allowed"),
        [
            (offset_date(-1), None, True),
            (None, offset_date(1), True),
            (offset_date(-1), offset_date(1), True),
            (offset_date(-1), offset_date(-2), True),
            (offset_date(2), offset_date(1), True),
            (offset_date(1), offset_date(2), False),
            (offset_date(1), offset_date(-1), False),
        ],
    )
    def test_is_posting_allowed(self, board, locked, allowed_from, allowed_until, is_time_allowed):
        board.locked = locked
        board.save()
        board.preferences.posting_allowed_from = allowed_from
        board.preferences.posting_allowed_until = allowed_until
        board.preferences.save()
        board.refresh_from_db()
        assert board.is_posting_allowed == (is_time_allowed and not locked)


class TestBoardPreferencesModel:
    def test_board_has_preferences(self, board):
        assert board.preferences is not None

    def test_preferences_name(self, board):
        assert str(board.preferences) == f"{board} preferences"

    def test_get_absolute_url(self, board):
        assert board.preferences.get_absolute_url() == f"/boards/{board.slug}/preferences/"

    def test_inverse_opacity(self, board):
        assert board.preferences.get_inverse_opacity == 1.0 - board.preferences.background_opacity

    @pytest.mark.parametrize("bg_type", ["c", "b"])
    @pytest.mark.parametrize("image", [None, lf("bg_image")])
    def test_save(self, board, bg_type, image):
        board.preferences.background_type = bg_type
        board.preferences.background_image = image
        board.preferences.save()
        board.refresh_from_db()
        expected_bg_type = bg_type if image is not None else "c"
        expected_image = image if expected_bg_type == "b" else None
        assert board.preferences.background_type == expected_bg_type
        assert board.preferences.background_image == expected_image

    def test_preferences_deleted_after_board_delete(self, board):
        preferences_pk = board.preferences.pk
        board.delete()
        pytest.raises(BoardPreferences.DoesNotExist, BoardPreferences.objects.get, pk=preferences_pk)


class TestTopicModel:
    def test_subject_max_length(self, topic):
        assert topic._meta.get_field("subject").max_length == 400  # noqa: PLR2004

    def test_object_name_is_subject(self, topic):
        assert str(topic) == topic.subject

    def test_get_topic_posts(self, topic, post_factory):
        post = post_factory(topic=topic)
        post_factory(topic=topic, parent=post)
        assert list(topic.get_posts) == list(Post.objects.filter(topic=topic, parent=None))

    def test_get_post_count(self, topic, topic_factory, post_factory):
        batch_post_count = 3
        post1 = post_factory(topic=topic)
        post2 = post_factory(topic=topic)
        post_factory.create_batch(batch_post_count, topic=topic, parent=post1)
        post_factory.create_batch(batch_post_count, topic=topic, parent=post2)
        topic2_post_count = batch_post_count + 1
        post_factory.create_batch(topic2_post_count, topic=topic_factory(board=topic.board))
        assert topic.get_post_count == Post.objects.count() - topic2_post_count

    def test_get_last_post_date(self, topic, post_factory):
        assert topic.get_last_post_date is None
        post = post_factory(topic=topic)
        topic.refresh_from_db()
        assert topic.get_last_post_date == date(post.created_at, "d/m/Y")
        with freeze_time(offset_date(days=-1)):
            post_factory(topic=topic)
        topic.refresh_from_db()
        assert topic.get_last_post_date == date(post.created_at, "d/m/Y")

    def test_get_absolute_url(self, topic):
        assert topic.get_absolute_url() == f"/boards/{topic.board.slug}/"

    def test_topic_deleted_after_board_delete(self, topic):
        topic.board.delete()
        pytest.raises(Topic.DoesNotExist, Topic.objects.get, pk=topic.pk)

    @pytest.mark.parametrize("board_locked", [True, False])
    @pytest.mark.parametrize("topic_locked", [True, False])
    def test_is_posting_allowed(self, topic, board_locked, topic_locked):
        topic.locked = topic_locked
        topic.save()
        topic.board.locked = board_locked
        topic.board.save()
        topic.refresh_from_db()
        assert topic.is_posting_allowed == (not topic_locked and not board_locked)


class TestPostModel:
    def test_content_max_length(self, post):
        assert post._meta.get_field("content").max_length == 1000  # noqa: PLR2004

    def test_object_name_is_content(self, post):
        assert str(post) == post.content

    def test_get_descendant_count(self, post, post_factory):
        batch_count = 5
        post_factory.create_batch(batch_count, topic=post.topic, parent=post)
        post_factory.create_batch(batch_count, topic=post.topic, parent=post_factory(topic=post.topic))
        assert Post.objects.count() == (batch_count + 1) * 2
        assert post.get_descendant_count == batch_count

        post2 = post_factory(topic=post.topic, parent=post)
        post_factory.create_batch(batch_count, topic=post.topic, parent=post2)
        post.refresh_from_db()
        assert post.get_descendant_count == batch_count * 2 + 1

    def assert_and_set_reaction_type(self, post, reaction_type):
        assert post.get_reaction_score() == 0
        post.topic.board.preferences.reaction_type = reaction_type
        post.topic.board.preferences.save()

    def test_get_reaction_score_like(self, post, reaction_factory):
        self.assert_and_set_reaction_type(post, "l")
        batch_count = 2
        reaction_factory.create_batch(batch_count, post=post)
        post.refresh_from_db()
        assert post.get_reaction_score() == batch_count

    def test_get_reaction_score_vote(self, post, reaction_factory):
        self.assert_and_set_reaction_type(post, "v")
        reaction_factory.reset_sequence(1)
        reaction_factory.create_batch(
            4,
            post=post,
            reaction_type="v",
            reaction_score=factory.Sequence(lambda n: 1 if n % 2 == 0 else -1),  # 2 upvotes, 2 downvotes
        )
        post.refresh_from_db()
        assert post.get_reaction_score() == (2, 2)

    def test_get_reaction_score_star(self, post, reaction_factory):
        self.assert_and_set_reaction_type(post, "s")
        reaction_factory.reset_sequence(1)
        reaction_factory.create_batch(
            4,
            post=post,
            reaction_type="s",
            reaction_score=factory.Sequence(lambda n: n),  # 1, 2, 3, 4
        )
        post.refresh_from_db()
        assert post.get_reaction_score() == f"{((1+2+3+4)/4):.2g}"

    def test_get_reaction_score_none(self, post):
        self.assert_and_set_reaction_type(post, "n")
        post.refresh_from_db()
        assert post.get_reaction_score() == 0

    def test_get_reaction_score_unknown(self, post):
        self.assert_and_set_reaction_type(post, "?")
        post.refresh_from_db()
        assert post.get_reaction_score() == 0
        assert post.topic.board.preferences.reaction_type == "?"  # TODO: convert charfields to textchoices

    def test_get_has_reacted(self, rf, post, user, reaction_factory):
        reaction_type = "l"
        post.topic.board.preferences.reaction_type = reaction_type
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

    @pytest.mark.parametrize("data_type", ADDITIONAL_DATA_TYPE_CHOICES)
    def test_get_additional_data(self, post, data_type, misc_data_factory, chemdoodle_data_factory):
        assert post.get_additional_data(additional_data_type=data_type) is None
        additional_data = None
        if data_type == "m":
            additional_data = misc_data_factory.create(post=post)
        elif data_type == "c":
            additional_data = chemdoodle_data_factory.create(post=post)
        if data_type in ["m", "c"]:  # files not yet implemented
            post.refresh_from_db()
            assert post.get_additional_data(additional_data_type=data_type) == additional_data

    def test_cleanup_image_uploads(self, topic, post_factory, post_image_factory):
        topic.board.preferences.allow_image_uploads = True
        topic.board.preferences.save()

        batch_count = 2
        post_image1, post_image2 = post_image_factory.create_batch(batch_count, board=topic.board)
        assert PostImage.objects.count() == batch_count
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
    def test_reaction_deleted_after_post_delete(self, reaction):
        reaction.post.delete()
        pytest.raises(Reaction.DoesNotExist, Reaction.objects.get, pk=reaction.pk)

    def test_reaction_deleted_after_topic_delete(self, reaction):
        reaction.post.topic.delete()
        pytest.raises(Reaction.DoesNotExist, Reaction.objects.get, pk=reaction.pk)

    def test_reaction_deleted_after_board_delete(self, reaction, topic_factory, post_factory, reaction_factory):
        topic2 = topic_factory(board=reaction.post.topic.board)
        post2 = post_factory(topic=topic2)
        reaction2 = reaction_factory(post=post2)
        reaction.post.topic.board.delete()
        pytest.raises(Reaction.DoesNotExist, Reaction.objects.get, pk=reaction.pk)
        pytest.raises(Reaction.DoesNotExist, Reaction.objects.get, pk=reaction2.pk)


# TODO: add tests for AdditionalData Model
class TestAdditionalDataModel:
    @pytest.mark.parametrize("data_type", ADDITIONAL_DATA_TYPE_CHOICES)
    def test_type_constraint(self, post, data_type, additional_data_factory):
        pytest.raises(IntegrityError, additional_data_factory.create_batch, size=2, post=post, data_type=data_type)

    @pytest.mark.parametrize("data_type", ADDITIONAL_DATA_TYPE_CHOICES)
    def test_correct_data_for_type(self, post, data_type, additional_data_factory, json_object):
        if data_type in ["m", "c"]:
            additional_data_factory.create(post=post, data_type=data_type, json=json_object)
            assert AdditionalData.objects.filter(post=post, data_type=data_type).count() == 1

    def test_additional_data_deleted_after_post_delete(self, additional_data):
        additional_data.post.delete()
        pytest.raises(AdditionalData.DoesNotExist, AdditionalData.objects.get, pk=additional_data.pk)

    def test_additional_data_deleted_after_topic_delete(self, additional_data):
        additional_data.post.topic.delete()
        pytest.raises(AdditionalData.DoesNotExist, AdditionalData.objects.get, pk=additional_data.pk)

    def test_additional_data_deleted_after_board_delete(self, additional_data):
        additional_data.post.topic.board.delete()
        pytest.raises(AdditionalData.DoesNotExist, AdditionalData.objects.get, pk=additional_data.pk)


class TestImageModel:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, image_factory):
        for image_format in IMAGE_FORMATS:
            for image_type, _ in IMAGE_TYPE:
                image_factory(
                    board=board if image_type == "p" else None,
                    image_type=image_type,
                    image__format=image_format,
                    image__filename=f"test.{image_format}",
                )

    @pytest.mark.parametrize("image_type", [image_type[0] for image_type in IMAGE_TYPE])
    def test_image_name_is_title(self, image_type):
        img = Image.objects.filter(image_type=image_type).first()
        assert str(img) == img.title

    @pytest.mark.parametrize("image_type", [image_type[0] for image_type in IMAGE_TYPE])
    def test_image_url(self, image_type):
        img = Image.objects.filter(image_type=image_type).first()
        ext = Path(img.image.name).suffix
        pattern = rf"^{settings.MEDIA_URL}images/{image_type}/[a-z0-9]+/[a-z0-9]{{2}}/{img.id}{ext}$"
        assert re.match(pattern, img.image.url)

    @pytest.mark.parametrize("image_type", [image_type[0] for image_type in IMAGE_TYPE])
    def test_image_max_dimensions(self, image_type):
        img = Image.objects.filter(image_type=image_type).first()
        if img.image_type == "p":
            assert img.image.width <= settings.MAX_POST_IMAGE_WIDTH
            assert img.image.height <= settings.MAX_POST_IMAGE_HEIGHT
        else:
            assert img.image.width <= settings.MAX_IMAGE_WIDTH
            assert img.image.height <= settings.MAX_IMAGE_HEIGHT

    @pytest.mark.parametrize("image_type", [image_type[0] for image_type in IMAGE_TYPE])
    def test_get_board_usage_count(self, board, image_type):
        img = Image.objects.filter(image_type=image_type).first()
        board.preferences.background_image = img
        board.preferences.background_type = "i"
        board.preferences.save()
        assert img.get_board_usage_count == (1 if image_type == "b" else 0)

    def test_get_image_dimensions(self):
        img = Image.objects.first()
        assert img.get_image_dimensions == f"{img.image.width}x{img.image.height}"

    def test_get_half_image_dimensions(self):
        img = Image.objects.first()
        assert img.get_half_image_dimensions == f"{img.image.width // 2}x{img.image.height // 2}"

    def test_get_small_thumbnail_dimensions(self):
        assert (
            Image.objects.first().get_small_thumbnail_dimensions
            == f"{settings.SMALL_THUMBNAIL_WIDTH}x{settings.SMALL_THUMBNAIL_HEIGHT}"
        )

    def test_get_webp(self):
        img = Image.objects.first()
        pilimage = PILImage.open(img.get_webp)
        assert pilimage.format == "WEBP"

    @pytest.mark.parametrize("image_type", [image_type[0] for image_type in IMAGE_TYPE])
    @pytest.mark.parametrize("alternate_resolution", settings.THUMBNAIL_ALTERNATIVE_RESOLUTIONS)
    def test_thumbnail_url_and_dimensions(self, image_type, alternate_resolution):
        img = Image.objects.filter(image_type=image_type).first()
        small_thumb = img.get_small_thumbnail
        large_thumb = img.get_large_thumbnail

        def check_thumb_exists(thumb):
            assert thumb is not None
            assert f"{settings.MEDIA_URL}cache/" in thumb.url
            assert default_storage.exists(Path(settings.MEDIA_ROOT) / thumb.name)

            name = Path(thumb.name).with_suffix("")
            ext = Path(thumb.name).suffix
            assert default_storage.exists(Path(settings.MEDIA_ROOT) / f"{name}@{alternate_resolution}x{ext}")

        def check_thumb_dimensions(thumb, width, height):
            assert thumb.width <= width
            assert thumb.height <= height

        def check_thumb(thumb, width, height):
            check_thumb_exists(thumb)
            check_thumb_dimensions(thumb, width, height)

        check_thumb(small_thumb, settings.SMALL_THUMBNAIL_WIDTH, settings.SMALL_THUMBNAIL_HEIGHT)
        check_thumb(large_thumb, img.image.width / 2, img.image.height / 2)

    @pytest.mark.parametrize("image_type", [image_type[0] for image_type in IMAGE_TYPE])
    def test_image_tag(self, image_type):
        img = Image.objects.filter(image_type=image_type).first()
        assert f'<img src="{escape(img.get_small_thumbnail.url)}" />' == img.image_tag

    def test_proxy_background_image(self, bg_image_factory):
        assert list(Image.objects.filter(image_type="b")) == list(BgImage.objects.all())

        count_before = BgImage.objects.count()
        bg_image_factory()
        assert BgImage.objects.count() == count_before + 1

    def test_proxy_post_image(self, post_image_factory):
        assert list(Image.objects.filter(image_type="p")) == list(PostImage.objects.all())

        count_before = PostImage.objects.count()
        post_image_factory()
        assert PostImage.objects.count() == count_before + 1


class TestExportModel:
    @pytest.mark.parametrize(("topic_count"), [1, 5])
    @pytest.mark.parametrize(("post_count"), [0, 1, 10])
    def test_export_save(self, board, topic_factory, post_factory, topic_count, post_count):
        topics = topic_factory.create_batch(topic_count, board=board)

        # want posts in different topics to have mixed created times
        for _ in range(post_count):
            for topic in topics:
                post_factory(topic=topic)

        csv_output = StringIO()
        writer = csv.writer(csv_output)

        writer.writerow(Export.HEADER.values())
        for topic in topics:
            for post in topic.posts.values_list(*Export.HEADER.keys()):
                writer.writerow(post)
        expected_file_content = csv_output.getvalue()

        export = Export.objects.create(board=board)
        assert export.post_count == topic_count * post_count
        with export.file.open() as file:
            file_content = file.read().decode()

        assert file_content == expected_file_content

    @pytest.mark.parametrize(
        ("initial_export_count", "expected_exports"),
        [
            (Export.MAX_COUNT - 2, Export.MAX_COUNT - 1),
            (Export.MAX_COUNT, Export.MAX_COUNT),
            (Export.MAX_COUNT + 2, Export.MAX_COUNT),
        ],
    )
    def test_export_save_max_count(self, board, initial_export_count, expected_exports):
        for _ in range(initial_export_count):
            Export.objects.create(board=board)

        new_export = Export(board=board)
        new_export.save()

        assert Export.objects.filter(board=board).count() == expected_exports

    def test_oldest_max_count_export_deleted(self, board, export_factory):
        export_factory.create_batch(Export.MAX_COUNT, board=board)
        oldest_export = Export.objects.filter(board=board).order_by("created_at").first()
        export_factory(board=board)

        exports = Export.objects.filter(board=board)
        assert exports.count() == Export.MAX_COUNT
        assert oldest_export not in exports
