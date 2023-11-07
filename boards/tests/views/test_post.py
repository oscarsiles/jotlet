import json
import shutil
from http import HTTPStatus

import pytest
from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from pytest_django.asserts import assertContains, assertNotContains
from pytest_lazy_fixtures import lf

from boards.models import REACTION_TYPE, Image, Post
from boards.routing import websocket_urlpatterns
from boards.tests.utils import create_image
from jotlet.utils import offset_date


@pytest.fixture(autouse=True)
def _set_user3_board_moderator(board, user3):
    board.preferences.moderators.add(user3)
    board.preferences.save()


class TestPostCreateView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, topic):
        self.post_create_url = reverse("boards:post-create", kwargs={"slug": board.slug, "topic_pk": topic.pk})

    def test_anonymous_permissions(self, client):
        response = client.get(self.post_create_url)
        assert response.status_code == HTTPStatus.OK
        response = client.post(self.post_create_url, data={"content": "Test Message anon"})
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Post.objects.first().content == "Test Message anon"

    def test_replies_permissions_anonymous(self, client, post):
        reply_url = reverse(
            "boards:post-reply",
            kwargs={"slug": post.topic.board.slug, "topic_pk": post.topic.pk, "post_pk": post.pk},
        )
        response = client.get(reply_url)
        assert response.status_code == HTTPStatus.FOUND

        post.topic.board.preferences.board_type = "r"
        post.topic.board.preferences.save()
        response = client.get(reply_url)
        assert response.status_code == HTTPStatus.FOUND

        post.topic.board.preferences.allow_guest_replies = True
        post.topic.board.preferences.save()
        response = client.get(reply_url)
        assert response.status_code == HTTPStatus.OK

        post.approved = False
        post.save()
        response = client.get(reply_url)
        assert response.status_code == HTTPStatus.FOUND

    def test_replies_permissions_owner(self, client, post, user):
        client.force_login(user)
        reply_url = reverse(
            "boards:post-reply",
            kwargs={"slug": post.topic.board.slug, "topic_pk": post.topic.pk, "post_pk": post.pk},
        )
        response = client.get(reply_url)
        assert response.status_code == HTTPStatus.FORBIDDEN

        post.topic.board.preferences.board_type = "r"
        post.topic.board.preferences.save()
        response = client.get(reply_url)
        assert response.status_code == HTTPStatus.OK

        post.approved = False
        post.save()
        response = client.get(reply_url)
        assert response.status_code == HTTPStatus.OK

    def test_reply(self, client, post):
        reply_url = reverse(
            "boards:post-reply",
            kwargs={"slug": post.topic.board.slug, "topic_pk": post.topic.pk, "post_pk": post.pk},
        )
        post.topic.board.preferences.board_type = "r"
        post.topic.board.preferences.allow_guest_replies = True
        post.topic.board.preferences.save()

        client.post(reply_url, data={"content": "Test Message reply"})
        reply = Post.objects.get(content="Test Message reply")
        assert reply.topic == post.topic
        assert reply.parent == post

    def test_post_session_key(self, client):
        client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        assert client.session.session_key == Post.objects.get(content="Test Post").session_key

    def test_post_approval(self, client, board, user, user2, user3):
        board.preferences.require_post_approval = True
        board.preferences.save()
        client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        assert Post.objects.get(content="Test Post").approved is False

        client.force_login(user)
        client.post(
            self.post_create_url,
            data={"content": "Test Post user1"},
        )
        assert Post.objects.get(content="Test Post user1").approved is True  # Board owner can post without approval

        client.force_login(user2)
        client.post(
            self.post_create_url,
            data={"content": "Test Post user2"},
        )
        assert Post.objects.get(content="Test Post user2").approved is False  # Normal user needs approval

        client.force_login(user3)
        client.post(
            self.post_create_url,
            data={"content": "Test Post user3"},
        )
        assert Post.objects.get(content="Test Post user3").approved is True  # Moderator can post without approval

    @pytest.mark.parametrize("locked_object", ["board", "topic"])
    @pytest.mark.parametrize(
        ("test_user", "expected_response_get", "expected_response_post"),
        [
            (None, 302, 302),
            (lf("user2"), 403, 403),
            (lf("user"), 200, 204),
            (lf("user_staff"), 200, 204),
        ],
    )
    def test_locked(self, client, topic, locked_object, test_user, expected_response_get, expected_response_post):
        if locked_object == "board":
            topic.board.locked = True
            topic.board.save()
        elif locked_object == "topic":
            topic.locked = True
            topic.save()
        if test_user is not None:
            client.force_login(test_user)
        response = client.get(self.post_create_url)
        assert response.status_code == expected_response_get
        response = client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        assert response.status_code == expected_response_post
        if expected_response_post == HTTPStatus.NO_CONTENT:
            assert Post.objects.count() == 1
        else:
            pytest.raises(Post.DoesNotExist, Post.objects.get, content="Test Post")
            assert Post.objects.count() == 0

    @pytest.mark.parametrize(
        ("allowed_from", "allowed_until", "expected_response"),
        [
            (offset_date(days=-1), None, HTTPStatus.NO_CONTENT),
            (None, offset_date(days=1), HTTPStatus.NO_CONTENT),
            (offset_date(days=-1), offset_date(days=1), HTTPStatus.NO_CONTENT),
            (offset_date(days=-1), offset_date(days=-2), HTTPStatus.NO_CONTENT),
            (offset_date(days=2), offset_date(days=1), HTTPStatus.NO_CONTENT),
            (offset_date(days=1), offset_date(days=2), HTTPStatus.FOUND),
            (offset_date(days=1), offset_date(days=-1), HTTPStatus.FOUND),
        ],
    )
    def test_post_allowed_time(self, client, board, allowed_from, allowed_until, expected_response):
        board.preferences.posting_allowed_from = allowed_from
        board.preferences.posting_allowed_until = allowed_until
        board.preferences.save()
        assert Post.objects.count() == 0
        response = client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        assert response.status_code == expected_response
        if expected_response == HTTPStatus.NO_CONTENT:
            assert Post.objects.count() == 1
        else:
            assert Post.objects.count() == 0

    @pytest.mark.parametrize(
        ("allowed_from", "allowed_until"),
        [
            (offset_date(days=1), offset_date(days=2)),
            (offset_date(days=1), offset_date(days=1)),
        ],
    )
    def test_post_outside_window(self, client, board, allowed_from, allowed_until):
        board.preferences.posting_allowed_from = allowed_from
        board.preferences.posting_allowed_until = allowed_until
        board.preferences.save()
        response = client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        assert response.status_code == HTTPStatus.FOUND
        pytest.raises(Post.DoesNotExist, Post.objects.get, content="Test Post")

    @pytest.mark.asyncio()
    @pytest.mark.django_db(transaction=True)
    async def test_post_created_websocket_message(self, client, board, topic, user):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(self.post_create_url, data={"content": "Test Post"})
        post = await Post.objects.aget(content="Test Post")
        assert post is not None
        message = await communicator.receive_from()
        assert "post_created" in message
        assert f'"topic_pk": "{topic.pk!s}"' in message
        await communicator.disconnect()


class TestPostUpdateView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, topic, post):
        self.post_updated_url = reverse(
            "boards:post-update", kwargs={"slug": board.slug, "topic_pk": topic.pk, "pk": post.pk}
        )

    def test_anonymous_permissions(self, client, topic):
        response = client.post(
            reverse("boards:post-create", kwargs={"slug": topic.board.slug, "topic_pk": topic.pk}),
            data={"content": "Test Post anon"},
        )
        post = Post.objects.get(content="Test Post anon")
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert client.session.session_key == post.session_key
        response = client.post(
            reverse("boards:post-update", kwargs={"slug": topic.board.slug, "topic_pk": topic.pk, "pk": post.pk}),
            data={"content": "Test Post anon NEW"},
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Post.objects.get(pk=post.pk).content == "Test Post anon NEW"

    def test_other_user_permissions(self, client, user2):
        client.force_login(user2)
        response = client.get(self.post_updated_url)
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_board_moderator_permissions(self, client, post, user3):
        client.force_login(user3)
        response = client.get(self.post_updated_url)
        assert response.status_code == HTTPStatus.OK
        response = client.post(
            self.post_updated_url,
            data={"content": "Test Post NEW"},
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Post.objects.get(pk=post.pk).content == "Test Post NEW"

    def test_owner_permissions(self, client, post, user):
        client.force_login(user)
        response = client.get(self.post_updated_url)
        assert response.status_code == HTTPStatus.OK
        response = client.post(
            self.post_updated_url,
            data={"content": "Test Post NEW"},
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Post.objects.get(pk=post.pk).content == "Test Post NEW"

    @pytest.mark.parametrize(
        ("test_user", "expected_response_get", "expected_response_post"),
        [
            (None, 302, 302),
            (lf("user"), HTTPStatus.OK, HTTPStatus.NO_CONTENT),  # board owner
            (lf("user2"), HTTPStatus.FORBIDDEN, HTTPStatus.FORBIDDEN),  # other user
            (lf("user3"), HTTPStatus.OK, HTTPStatus.NO_CONTENT),  # board moderator
            (lf("user_staff"), HTTPStatus.OK, HTTPStatus.NO_CONTENT),
        ],
    )
    def test_editing_forbidden(self, client, post, topic, test_user, expected_response_get, expected_response_post):
        post_updated_url = self.post_updated_url
        if test_user is not None:
            client.force_login(test_user)
            post.user = test_user
            post.save()
        else:
            client.post(
                reverse("boards:post-create", kwargs={"slug": topic.board.slug, "topic_pk": topic.pk}),
                data={"content": "Test Post anon"},
            )
            post = Post.objects.get(content="Test Post anon")
            post_updated_url = reverse(
                "boards:post-update", kwargs={"slug": topic.board.slug, "topic_pk": topic.pk, "pk": post.pk}
            )

        post.topic.board.preferences.allow_post_editing = False
        post.topic.board.preferences.save()
        original_content = post.content

        response = client.get(post_updated_url)
        assert response.status_code == expected_response_get

        response = client.post(
            post_updated_url,
            data={"content": "Test Post NEW"},
        )
        if expected_response_post == HTTPStatus.NO_CONTENT:
            assert response.status_code == HTTPStatus.NO_CONTENT
            assert Post.objects.get(pk=post.pk).content == "Test Post NEW"
        else:
            assert Post.objects.get(pk=post.pk).content == original_content

    @pytest.mark.parametrize(
        "locked_object",
        [
            lf("board"),
            lf("topic"),
        ],
    )
    @pytest.mark.parametrize(
        ("test_user", "expected_response_get", "expected_response_post"),
        [
            (None, 302, 302),
            (lf("user2"), 403, 403),
            (lf("user"), 200, 204),  # owner
            (lf("user3"), 200, 204),  # moderator
            (lf("user_staff"), 200, 204),
        ],
    )
    def test_locked(self, client, post, locked_object, test_user, expected_response_get, expected_response_post):
        if test_user is not None:
            client.force_login(test_user)
            post.user = test_user
        else:
            response = client.post(
                reverse("boards:post-create", kwargs={"slug": post.topic.board.slug, "topic_pk": post.topic.pk}),
                data={"content": "Test Post anon"},
            )
            post = Post.objects.get(content="Test Post anon")
        original_content = post.content
        locked_object.locked = True
        locked_object.save()

        response = client.get(self.post_updated_url)
        assert response.status_code == expected_response_get
        response = client.post(
            self.post_updated_url,
            data={"content": "Test Post NEW"},
        )
        assert response.status_code == expected_response_post
        if expected_response_post == HTTPStatus.NO_CONTENT:
            assert Post.objects.get(pk=post.pk).content == "Test Post NEW"
        else:
            assert Post.objects.get(pk=post.pk).content == original_content

    @pytest.mark.asyncio()
    @pytest.mark.django_db(transaction=True)
    async def test_post_updated_websocket_message(self, client, board, post, user):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(self.post_updated_url, data={"content": "Test Post NEW"})
        message = await communicator.receive_from()
        assert "post_updated" in message
        assert f'"post_pk": "{post.pk!s}"' in message
        await communicator.disconnect()


class TestPostDeleteView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, topic, post):
        self.post_deleted_url = reverse(
            "boards:post-delete", kwargs={"slug": board.slug, "topic_pk": topic.pk, "pk": post.pk}
        )

    def test_anonymous_permissions(self, client, topic):
        response = client.post(self.post_deleted_url)
        assert response.status_code == HTTPStatus.FOUND
        assert Post.objects.count() == 1
        client.post(
            reverse("boards:post-create", kwargs={"slug": topic.board.slug, "topic_pk": topic.pk}),
            data={"content": "Test Post anon"},
        )
        post2 = Post.objects.get(content="Test Post anon")
        assert Post.objects.count() == 2  # noqa: PLR2004
        client.post(
            reverse("boards:post-delete", kwargs={"slug": topic.board.slug, "topic_pk": topic.pk, "pk": post2.pk})
        )
        assert Post.objects.count() == 1

    def test_other_user_permissions(self, client, user2):
        client.force_login(user2)
        response = client.post(self.post_deleted_url)
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Post.objects.count() == 1

    def test_board_moderator_permissions(self, client, user3):
        client.force_login(user3)
        response = client.post(self.post_deleted_url)
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Post.objects.count() == 0

    def test_owner_permissions(self, client, user):
        client.force_login(user)
        response = client.post(self.post_deleted_url)
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Post.objects.count() == 0

    @pytest.mark.asyncio()
    @pytest.mark.django_db(transaction=True)
    async def test_post_deleted_websocket_message(self, client, board, post, user):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(self.post_deleted_url)
        message = await communicator.receive_from()
        assert "post_deleted" in message
        assert f'"post_pk": "{post.pk!s}"' in message
        await communicator.disconnect()


#  TODO: test post approvals by topic/board
class TestApprovePostsView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, topic, topic_factory, post_factory):
        board.preferences.require_post_approval = True
        board.preferences.save()
        topic2 = topic_factory(board=board)

        self.first_batch_count = 10
        self.second_batch_count = 20
        self.total_posts = self.first_batch_count + self.second_batch_count
        post_factory.create_batch(self.first_batch_count, topic=topic, approved=False)
        post_factory.create_batch(self.second_batch_count, topic=topic2, approved=False)

    @pytest.fixture()
    def board_posts_approve_url(self, board):
        return reverse("boards:board-posts-approve", kwargs={"slug": board.slug})

    @pytest.fixture()
    def topic_posts_approve_url(self, board, topic):
        return reverse("boards:topic-posts-approve", kwargs={"slug": board.slug, "topic_pk": topic.pk})

    @pytest.mark.parametrize(
        ("test_user", "expected_response"),
        [
            (None, HTTPStatus.FOUND),
            (lf("user2"), HTTPStatus.FORBIDDEN),
            (lf("user"), HTTPStatus.OK),
            (lf("user_staff"), HTTPStatus.OK),
        ],
    )
    @pytest.mark.parametrize("url", [lf("topic_posts_approve_url"), lf("board_posts_approve_url")])
    def test_approve_permissions(self, client, test_user, expected_response, url):
        if test_user:
            client.force_login(test_user)
        response = client.get(url)
        assert response.status_code == expected_response

    def test_topic_posts_approve(self, client, board, topic, user, topic_posts_approve_url):
        client.force_login(user)
        assert Post.objects.filter(topic__board=board, approved=False).count() == self.total_posts
        response = client.post(topic_posts_approve_url)
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Post.objects.filter(topic=topic, approved=True).count() == self.first_batch_count
        assert Post.objects.filter(topic__board=board, approved=False).count() == self.second_batch_count

    def test_board_posts_approve(self, client, board, user, board_posts_approve_url):
        client.force_login(user)
        assert Post.objects.filter(topic__board=board, approved=False).count() == self.total_posts
        response = client.post(board_posts_approve_url)
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Post.objects.filter(topic__board=board, approved=True).count() == self.total_posts

    @pytest.mark.asyncio()
    @pytest.mark.django_db(transaction=True)
    async def test_topic_posts_approved_websocket_message(self, client, board, user, topic_posts_approve_url):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(topic_posts_approve_url)
        message = await communicator.receive_from()
        assert "topic_updated" in message
        await communicator.disconnect()

    @pytest.mark.asyncio()
    @pytest.mark.django_db(transaction=True)
    async def test_board_posts_approved_websocket_message(self, client, board, user, board_posts_approve_url):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(board_posts_approve_url)
        message = await communicator.receive_from()
        assert "board_updated" in message
        await communicator.disconnect()


class TestDeletePostsView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, topic, topic_factory, post_factory):
        topic2 = topic_factory(board=board)

        self.first_topic_count = 10
        self.second_topic_count = 20
        self.total_posts = self.first_topic_count + self.second_topic_count
        post_factory.create_batch(self.first_topic_count, topic=topic)
        post_factory.create_batch(self.second_topic_count, topic=topic2)

    @pytest.fixture()
    def board_posts_delete_url(self, board):
        return reverse("boards:board-posts-delete", kwargs={"slug": board.slug})

    @pytest.fixture()
    def topic_posts_delete_url(self, board, topic):
        return reverse("boards:topic-posts-delete", kwargs={"slug": board.slug, "topic_pk": topic.pk})

    @pytest.mark.parametrize(
        ("test_user", "expected_response"),
        [
            (None, HTTPStatus.FOUND),
            (lf("user2"), HTTPStatus.FORBIDDEN),
            (lf("user"), HTTPStatus.OK),
            (lf("user_staff"), HTTPStatus.OK),
        ],
    )
    @pytest.mark.parametrize("url", [lf("topic_posts_delete_url"), lf("board_posts_delete_url")])
    def test_delete_permissions(self, client, test_user, expected_response, url):
        if test_user:
            client.force_login(test_user)
        response = client.get(url)
        assert response.status_code == expected_response

    def test_topic_posts_delete(self, client, board, topic, user, topic_posts_delete_url):
        client.force_login(user)
        assert Post.objects.filter(topic__board=board).count() == self.total_posts
        response = client.post(topic_posts_delete_url)
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Post.objects.filter(topic=topic).count() == 0
        assert Post.objects.filter(topic__board=board).count() == self.second_topic_count

    def test_board_posts_delete(self, client, board, user, board_posts_delete_url):
        client.force_login(user)
        assert Post.objects.filter(topic__board=board).count() == self.total_posts
        response = client.post(board_posts_delete_url)
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Post.objects.filter(topic__board=board).count() == 0

    @pytest.mark.asyncio()
    @pytest.mark.django_db(transaction=True)
    async def test_topic_posts_deleted_websocket_message(self, client, board, topic, user, topic_posts_delete_url):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        post_count = await Post.objects.filter(topic=topic).acount()
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(topic_posts_delete_url)
        for _ in range(post_count):
            message = await communicator.receive_from()
            assert "post_deleted" in message
        await communicator.disconnect()

    @pytest.mark.asyncio()
    @pytest.mark.django_db(transaction=True)
    async def test_board_posts_deleted_websocket_message(self, client, board, user, board_posts_delete_url):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        post_count = await Post.objects.filter(topic__board=board).acount()
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(board_posts_delete_url)
        for _ in range(post_count):
            message = await communicator.receive_from()
            assert "post_deleted" in message
        await communicator.disconnect()


class TestPostFetchView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, topic, post):
        board.preferences.require_post_approval = True
        board.preferences.save()
        post.approved = False
        post.save()
        self.post_fetch_url = reverse(
            "boards:post-fetch", kwargs={"slug": board.slug, "topic_pk": topic.pk, "pk": post.pk}
        )

    def test_post_fetch_require_no_approval(self, client, board, post):
        board.preferences.require_post_approval = False
        board.preferences.save()
        response = client.get(self.post_fetch_url)
        assert response.status_code == HTTPStatus.OK
        assert response.context["post"] == post
        assertContains(response, post.content, html=True)

    def test_post_fetch_approved(self, client, board, post):
        board.preferences.require_post_approval = True
        board.preferences.save()
        post.approved = True
        post.save()
        response = client.get(self.post_fetch_url)
        assert response.status_code == HTTPStatus.OK
        assert response.context["post"] == post
        assertContains(response, post.content, html=True)

    def test_post_fetch_content_anonymous_not_approved(self, client, board, post):
        client.get(reverse("boards:board", kwargs={"slug": board.slug}))
        response = client.get(self.post_fetch_url)
        assertNotContains(response, post.content, html=True)

    def test_post_fetch_content_anonymous_not_approved_own_post(self, client, board, post):
        response = client.post(
            reverse("boards:post-create", kwargs={"slug": board.slug, "topic_pk": post.topic.pk}),
            data={"content": "Test Post anon"},
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        post = Post.objects.get(content="Test Post anon")
        response = client.get(
            reverse("boards:post-fetch", kwargs={"slug": board.slug, "topic_pk": post.topic.pk, "pk": post.pk})
        )
        assertContains(response, post.content, html=True)

    def test_post_fetch_content_other_user_not_approved(self, client, board, post, user2):
        client.force_login(user2)
        client.get(reverse("boards:board", kwargs={"slug": board.slug}))

        response = client.get(self.post_fetch_url)
        assertNotContains(response, post.content, html=True)

    def test_post_fetch_content_other_user_not_approved_own_post(self, client, board, post, user2):
        client.force_login(user2)
        response = client.post(
            reverse("boards:post-create", kwargs={"slug": board.slug, "topic_pk": post.topic.pk}),
            data={"content": "Test Post anon"},
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        post = Post.objects.get(content="Test Post anon")
        response = client.get(
            reverse("boards:post-fetch", kwargs={"slug": board.slug, "topic_pk": post.topic.pk, "pk": post.pk})
        )
        assertContains(response, post.content, html=True)

    def test_post_fetch_content_board_moderator_not_approved(self, client, post, user3):
        client.force_login(user3)
        response = client.get(self.post_fetch_url)
        assertContains(response, post.content, html=True)

    def test_post_fetch_content_owner_not_approved(self, client, post, user):
        client.force_login(user)
        response = client.get(self.post_fetch_url)
        assertContains(response, post.content, html=True)

    def test_post_fetch_content_can_approve_not_approved(self, client, post, user2):
        user2.user_permissions.add(Permission.objects.get(codename="can_approve_posts"))
        user2.save()
        client.force_login(user2)
        response = client.get(self.post_fetch_url)
        assertContains(response, post.content, html=True)


class TestPostFooterFetchView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, topic, post, user, reaction_factory):
        board.preferences.reaction_type = "l"
        board.preferences.save()
        for reaction_type in REACTION_TYPE[1:]:
            reaction_factory(post=post, reaction_type=reaction_type[0], user=user)

    @pytest.fixture()
    def post_footer_fetch_url(self, board, topic, post):
        return reverse(
            "boards:post-footer-fetch",
            kwargs={"slug": board.slug, "topic_pk": topic.pk, "pk": post.pk},
        )

    def set_reaction_icon(self, reaction_type):
        icon = "bi-heart"  # default "l"
        if reaction_type == "v":
            icon = "bi-hand-thumbs-up"
        elif reaction_type == "s":
            icon = "bi-star"
        return icon

    @pytest.mark.parametrize("reaction_type", [reaction[0] for reaction in REACTION_TYPE[1:]])
    def test_post_footer_fetch_anonymous(self, client, post, reaction_type, post_footer_fetch_url):
        icon = self.set_reaction_icon(reaction_type)

        post.topic.board.preferences.reaction_type = reaction_type
        post.topic.board.preferences.save()
        post.approved = False
        post.save()

        response = client.get(post_footer_fetch_url)
        assert response.status_code == HTTPStatus.OK
        assert response.context["post"] == post
        assertNotContains(response, icon)

        post.approved = True
        post.save()
        response = client.get(post_footer_fetch_url)
        assert response.status_code == HTTPStatus.OK
        assert response.context["post"] == post
        assertContains(response, icon)

    @pytest.mark.parametrize("reaction_type", [reaction[0] for reaction in REACTION_TYPE[1:]])
    def test_post_footer_fetch_moderator(self, client, post, user3, reaction_type, post_footer_fetch_url):
        client.force_login(user3)

        icon = self.set_reaction_icon(reaction_type)

        post.topic.board.preferences.reaction_type = reaction_type
        post.topic.board.preferences.save()
        post.approved = False
        post.save()

        response = client.get(post_footer_fetch_url)
        assert response.status_code == HTTPStatus.OK
        assert response.context["post"] == post
        assertContains(response, icon)

        post.approved = True
        post.save()
        response = client.get(post_footer_fetch_url)
        assert response.status_code == HTTPStatus.OK
        assert response.context["post"] == post
        assertContains(response, icon)


class TestPostToggleApprovalView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, topic, post):
        board.preferences.require_post_approval = True
        board.preferences.save()
        post.approved = False
        post.save()

    @pytest.fixture()
    def post_approval_url(self, board, topic, post):
        return reverse(
            "boards:post-toggle-approval",
            kwargs={"slug": board.slug, "topic_pk": topic.pk, "pk": post.pk},
        )

    def test_post_toggle_approval_anonymous(self, client, post, post_approval_url):
        assert not post.approved
        response = client.post(post_approval_url)
        assert response.status_code == HTTPStatus.FOUND
        post.refresh_from_db()
        assert not post.approved

    def test_post_toggle_approval_other_user(self, client, post, user2, post_approval_url):
        client.force_login(user2)
        assert not post.approved
        response = client.post(post_approval_url)
        assert response.status_code == HTTPStatus.FORBIDDEN
        post.refresh_from_db()
        assert not post.approved

    @pytest.mark.parametrize(
        "test_user",
        [
            lf("user"),
            lf("user3"),
            lf("user_staff"),
        ],
    )
    def test_post_toggle_approval_authorized_user(self, client, post, test_user, post_approval_url):
        client.force_login(test_user)
        assert not post.approved
        response = client.post(post_approval_url)
        assert response.status_code == HTTPStatus.NO_CONTENT
        post.refresh_from_db()
        assert post.approved
        response = client.post(post_approval_url)
        assert response.status_code == HTTPStatus.NO_CONTENT
        post.refresh_from_db()
        assert not post.approved

    @pytest.mark.asyncio()
    @pytest.mark.django_db(transaction=True)
    async def test_post_toggle_websocket_message(self, client, board, post, user, post_approval_url):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(post_approval_url)
        message = await communicator.receive_from()
        assert "post_updated" in message
        assert f'"post_pk": "{post.pk!s}"' in message
        await sync_to_async(client.post)(post_approval_url)
        message = await communicator.receive_from()
        assert "post_updated" in message
        assert f'"post_pk": "{post.pk!s}"' in message
        await communicator.disconnect()


class TestPostImageUploadView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board):
        board.preferences.allow_image_uploads = True
        board.preferences.save()

    @pytest.fixture()
    def upload_url(self, board):
        return reverse("boards:post-image-upload", kwargs={"slug": board.slug})

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def post_image_and_assert(self, client, upload_url, image_type, test_user, expected_response_post):
        response = client.post(
            upload_url,
            {
                "image": SimpleUploadedFile(
                    f"{test_user}.png",
                    create_image(image_type.split("/")[1]),
                    content_type=image_type,
                )
            },
        )
        assert response.status_code == expected_response_post
        if response.status_code != HTTPStatus.OK:
            assert Image.objects.count() == self.expected_image_count
        else:
            image = Image.objects.order_by("created_at").last()
            data = json.loads(response.content)
            assert data["data"]["filePath"] == image.image.url

    @pytest.mark.parametrize(
        ("test_user", "expected_response_get", "expected_response_post"),
        [
            (None, HTTPStatus.FOUND, HTTPStatus.FOUND),
            (lf("user2"), HTTPStatus.FORBIDDEN, HTTPStatus.FORBIDDEN),
            (lf("user"), HTTPStatus.METHOD_NOT_ALLOWED, HTTPStatus.OK),
            (lf("user_staff"), HTTPStatus.METHOD_NOT_ALLOWED, HTTPStatus.OK),
        ],
    )
    @pytest.mark.parametrize("image_type", ["image/png", "image/jpeg", "image/bmp", "image/webp"])
    def test_permissions(
        self, client, board, test_user, expected_response_get, expected_response_post, upload_url, image_type
    ):
        if test_user is not None:
            client.force_login(test_user)
        response = client.get(upload_url)
        assert response.status_code == expected_response_get

        self.expected_image_count = 0
        self.post_image_and_assert(client, upload_url, image_type, test_user, expected_response_post)
        if expected_response_post == HTTPStatus.OK:
            self.expected_image_count = 1

        board.preferences.allow_image_uploads = False
        board.preferences.save()

        self.post_image_and_assert(
            client, upload_url, "image/png", test_user, HTTPStatus.FORBIDDEN if test_user else HTTPStatus.FOUND
        )

    def test_upload_image_over_max_count(self, client, user_staff, upload_url):
        client.force_login(user_staff)
        # sourcery skip: no-loop-in-tests
        for i in range(settings.MAX_POST_IMAGE_COUNT + 1):
            response = client.post(
                upload_url,
                {"image": SimpleUploadedFile(f"test{i}.png", create_image("png"), content_type="image/png")},
            )
            data = json.loads(response.content)
            if i < settings.MAX_POST_IMAGE_COUNT:
                assert data["data"]["filePath"] == Image.objects.order_by("created_at").last().image.url
            else:
                assert data["error"] == "Board image quota exceeded"

    def test_upload_invalid_image(self, client, user_staff, upload_url):
        client.force_login(user_staff)
        response = client.post(
            upload_url,
            {"image": SimpleUploadedFile("test.avif", create_image("avif"), content_type="image/avif")},
        )
        data = json.loads(response.content)
        assert data["error"] == "Invalid image type (only PNG, JPEG, GIF, BMP, and WEBP are allowed)"
