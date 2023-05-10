import datetime
import json
import shutil

import pytest
from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertContains, assertNotContains
from pytest_lazyfixture import lazy_fixture

from boards.models import REACTION_TYPE, Image, Post
from boards.routing import websocket_urlpatterns
from boards.tests.utils import create_image


@pytest.fixture(autouse=True)
def set_user3_board_moderator(board, user3):
    board.preferences.moderators.add(user3)
    board.preferences.save()


class TestPostCreateView:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, board, topic):
        self.post_create_url = reverse("boards:post-create", kwargs={"slug": board.slug, "topic_pk": topic.pk})

    def test_anonymous_permissions(self, client):
        response = client.get(self.post_create_url)
        assert response.status_code == 200
        response = client.post(self.post_create_url, data={"content": "Test Message anon"})
        assert response.status_code == 204
        assert Post.objects.first().content == "Test Message anon"

    def test_replies_permissions_anonymous(self, client, post):
        reply_url = reverse(
            "boards:post-reply",
            kwargs={"slug": post.topic.board.slug, "topic_pk": post.topic.pk, "post_pk": post.pk},
        )
        response = client.get(reply_url)
        assert response.status_code == 302

        post.topic.board.preferences.type = "r"
        post.topic.board.preferences.save()
        response = client.get(reply_url)
        assert response.status_code == 302

        post.topic.board.preferences.allow_guest_replies = True
        post.topic.board.preferences.save()
        response = client.get(reply_url)
        assert response.status_code == 200

        post.approved = False
        post.save()
        response = client.get(reply_url)
        assert response.status_code == 302

    def test_replies_permissions_owner(self, client, post, user):
        client.force_login(user)
        reply_url = reverse(
            "boards:post-reply",
            kwargs={"slug": post.topic.board.slug, "topic_pk": post.topic.pk, "post_pk": post.pk},
        )
        response = client.get(reply_url)
        assert response.status_code == 403

        post.topic.board.preferences.type = "r"
        post.topic.board.preferences.save()
        response = client.get(reply_url)
        assert response.status_code == 200

        post.approved = False
        post.save()
        response = client.get(reply_url)
        assert response.status_code == 200

    def test_reply(self, client, post):
        reply_url = reverse(
            "boards:post-reply",
            kwargs={"slug": post.topic.board.slug, "topic_pk": post.topic.pk, "post_pk": post.pk},
        )
        post.topic.board.preferences.type = "r"
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
        "test_user,expected_response_get,expected_response_post",
        [
            (None, 302, 302),
            (lazy_fixture("user2"), 403, 403),
            (lazy_fixture("user"), 200, 204),
            (lazy_fixture("user_staff"), 200, 204),
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
        if expected_response_post == 204:
            assert Post.objects.count() == 1
        else:
            pytest.raises(Post.DoesNotExist, Post.objects.get, content="Test Post")
            assert Post.objects.count() == 0

    @pytest.mark.parametrize(
        "allowed_from,allowed_until,expected_response",
        [
            (timezone.now() - datetime.timedelta(days=1), None, 204),
            (None, timezone.now() + datetime.timedelta(days=1), 204),
            (timezone.now() - datetime.timedelta(days=1), timezone.now() + datetime.timedelta(days=1), 204),
            (timezone.now() - datetime.timedelta(days=1), timezone.now() - datetime.timedelta(days=2), 204),
            (timezone.now() + datetime.timedelta(days=2), timezone.now() + datetime.timedelta(days=1), 204),
            (timezone.now() + datetime.timedelta(days=1), timezone.now() + datetime.timedelta(days=2), 302),
            (timezone.now() + datetime.timedelta(days=1), timezone.now() - datetime.timedelta(days=1), 302),
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
        if expected_response == 204:
            assert Post.objects.count() == 1
        else:
            assert Post.objects.count() == 0

    @pytest.mark.parametrize(
        "allowed_from,allowed_until",
        [
            (timezone.now() + datetime.timedelta(days=1), timezone.now() + datetime.timedelta(days=2)),
            (timezone.now() + datetime.timedelta(days=1), timezone.now() - datetime.timedelta(days=1)),
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
        assert response.status_code == 302
        pytest.raises(Post.DoesNotExist, Post.objects.get, content="Test Post")

    @pytest.mark.asyncio
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
        assert f'"topic_pk": "{str(topic.pk)}"' in message
        await communicator.disconnect()


class TestPostUpdateView:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, board, topic, post):
        self.post_updated_url = reverse(
            "boards:post-update", kwargs={"slug": board.slug, "topic_pk": topic.pk, "pk": post.pk}
        )

    def test_anonymous_permissions(self, client, topic):
        response = client.post(
            reverse("boards:post-create", kwargs={"slug": topic.board.slug, "topic_pk": topic.pk}),
            data={"content": "Test Post anon"},
        )
        post = Post.objects.get(content="Test Post anon")
        assert response.status_code == 204
        assert client.session.session_key == post.session_key
        response = client.post(
            reverse("boards:post-update", kwargs={"slug": topic.board.slug, "topic_pk": topic.pk, "pk": post.pk}),
            data={"content": "Test Post anon NEW"},
        )
        assert response.status_code == 204
        assert Post.objects.get(pk=post.pk).content == "Test Post anon NEW"

    def test_other_user_permissions(self, client, user2):
        client.force_login(user2)
        response = client.get(self.post_updated_url)
        assert response.status_code == 403

    def test_board_moderator_permissions(self, client, post, user3):
        client.force_login(user3)
        response = client.get(self.post_updated_url)
        assert response.status_code == 200
        response = client.post(
            self.post_updated_url,
            data={"content": "Test Post NEW"},
        )
        assert response.status_code == 204
        assert Post.objects.get(pk=post.pk).content == "Test Post NEW"

    def test_owner_permissions(self, client, post, user):
        client.force_login(user)
        response = client.get(self.post_updated_url)
        assert response.status_code == 200
        response = client.post(
            self.post_updated_url,
            data={"content": "Test Post NEW"},
        )
        assert response.status_code == 204
        assert Post.objects.get(pk=post.pk).content == "Test Post NEW"

    @pytest.mark.parametrize(
        "test_user,expected_response_get,expected_response_post",
        [
            (None, 302, 302),
            (lazy_fixture("user"), 200, 204),  # board owner
            (lazy_fixture("user2"), 403, 403),  # other user
            (lazy_fixture("user3"), 200, 204),  # board moderator
            (lazy_fixture("user_staff"), 200, 204),
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
        if expected_response_post == 204:
            assert response.status_code == 204
            assert Post.objects.get(pk=post.pk).content == "Test Post NEW"
        else:
            assert Post.objects.get(pk=post.pk).content == original_content

    @pytest.mark.parametrize(
        "locked_object",
        [
            lazy_fixture("board"),
            lazy_fixture("topic"),
        ],
    )
    @pytest.mark.parametrize(
        "test_user,expected_response_get,expected_response_post",
        [
            (None, 302, 302),
            (lazy_fixture("user2"), 403, 403),
            (lazy_fixture("user"), 200, 204),  # owner
            (lazy_fixture("user3"), 200, 204),  # moderator
            (lazy_fixture("user_staff"), 200, 204),
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
        if expected_response_post == 204:
            assert Post.objects.get(pk=post.pk).content == "Test Post NEW"
        else:
            assert Post.objects.get(pk=post.pk).content == original_content

    @pytest.mark.asyncio
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
        assert f'"post_pk": "{str(post.pk)}"' in message
        await communicator.disconnect()


class TestPostDeleteView:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, board, topic, post):
        self.post_deleted_url = reverse(
            "boards:post-delete", kwargs={"slug": board.slug, "topic_pk": topic.pk, "pk": post.pk}
        )

    def test_anonymous_permissions(self, client, topic):
        response = client.post(self.post_deleted_url)
        assert response.status_code == 302
        assert Post.objects.count() == 1
        client.post(
            reverse("boards:post-create", kwargs={"slug": topic.board.slug, "topic_pk": topic.pk}),
            data={"content": "Test Post anon"},
        )
        post2 = Post.objects.get(content="Test Post anon")
        assert Post.objects.count() == 2
        client.post(
            reverse("boards:post-delete", kwargs={"slug": topic.board.slug, "topic_pk": topic.pk, "pk": post2.pk})
        )
        assert Post.objects.count() == 1

    def test_other_user_permissions(self, client, user2):
        client.force_login(user2)
        response = client.post(self.post_deleted_url)
        assert response.status_code == 403
        assert Post.objects.count() == 1

    def test_board_moderator_permissions(self, client, user3):
        client.force_login(user3)
        response = client.post(self.post_deleted_url)
        assert response.status_code == 204
        assert Post.objects.count() == 0

    def test_owner_permissions(self, client, user):
        client.force_login(user)
        response = client.post(self.post_deleted_url)
        assert response.status_code == 204
        assert Post.objects.count() == 0

    @pytest.mark.asyncio
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
        assert f'"post_pk": "{str(post.pk)}"' in message
        await communicator.disconnect()


#  TODO: test post approvals by topic/board
class TestApprovePostsView:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, board, topic, topic_factory, post_factory):
        board.preferences.require_post_approval = True
        board.preferences.save()
        self.topic_posts_approve_url = reverse(
            "boards:topic-posts-approve", kwargs={"slug": board.slug, "topic_pk": topic.pk}
        )
        self.board_posts_approve_url = reverse("boards:board-posts-approve", kwargs={"slug": board.slug})
        topic2 = topic_factory(board=board)
        post_factory.create_batch(10, topic=topic, approved=False)
        post_factory.create_batch(10, topic=topic2, approved=False)

    @pytest.mark.parametrize(
        "test_user,expected_response",
        [
            (None, 302),
            (lazy_fixture("user2"), 403),
            (lazy_fixture("user"), 200),
            (lazy_fixture("user_staff"), 200),
        ],
    )
    def test_approve_permissions(self, client, test_user, expected_response):
        if test_user:
            client.force_login(test_user)
        response = client.get(self.topic_posts_approve_url)
        assert response.status_code == expected_response
        response = client.get(self.board_posts_approve_url)
        assert response.status_code == expected_response

    def test_topic_posts_approve(self, client, board, topic, user):
        client.force_login(user)
        assert Post.objects.filter(topic__board=board, approved=False).count() == 20
        response = client.post(self.topic_posts_approve_url)
        assert response.status_code == 204
        assert Post.objects.filter(topic=topic, approved=True).count() == 10
        assert Post.objects.filter(topic__board=board, approved=False).count() == 10

    def test_board_posts_approve(self, client, board, user):
        client.force_login(user)
        assert Post.objects.filter(topic__board=board, approved=False).count() == 20
        response = client.post(self.board_posts_approve_url)
        assert response.status_code == 204
        assert Post.objects.filter(topic__board=board, approved=True).count() == 20

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_topic_posts_approved_websocket_message(self, client, board, user):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(self.topic_posts_approve_url)
        message = await communicator.receive_from()
        assert "topic_updated" in message
        await communicator.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_board_posts_approved_websocket_message(self, client, board, user):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(self.board_posts_approve_url)
        message = await communicator.receive_from()
        assert "board_updated" in message
        await communicator.disconnect()


class TestDeletePostsView:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, board, topic, topic_factory, post_factory):
        self.topic_posts_delete_url = reverse(
            "boards:topic-posts-delete", kwargs={"slug": board.slug, "topic_pk": topic.pk}
        )
        self.board_posts_delete_url = reverse("boards:board-posts-delete", kwargs={"slug": board.slug})
        topic2 = topic_factory(board=board)
        post_factory.create_batch(10, topic=topic)
        post_factory.create_batch(10, topic=topic2)

    @pytest.mark.parametrize(
        "test_user,expected_response",
        [
            (None, 302),
            (lazy_fixture("user2"), 403),
            (lazy_fixture("user"), 200),
            (lazy_fixture("user_staff"), 200),
        ],
    )
    def test_delete_permissions(self, client, test_user, expected_response):
        if test_user:
            client.force_login(test_user)
        response = client.get(self.topic_posts_delete_url)
        assert response.status_code == expected_response
        response = client.get(self.board_posts_delete_url)
        assert response.status_code == expected_response

    def test_topic_posts_delete(self, client, board, topic, user):
        client.force_login(user)
        assert Post.objects.filter(topic__board=board).count() == 20
        response = client.post(self.topic_posts_delete_url)
        assert response.status_code == 204
        assert Post.objects.filter(topic=topic).count() == 0
        assert Post.objects.filter(topic__board=board).count() == 10

    def test_board_posts_delete(self, client, board, user):
        client.force_login(user)
        assert Post.objects.filter(topic__board=board).count() == 20
        response = client.post(self.board_posts_delete_url)
        assert response.status_code == 204
        assert Post.objects.filter(topic__board=board).count() == 0

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_topic_posts_deleted_websocket_message(self, client, board, topic, user):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        post_count = await Post.objects.filter(topic=topic).acount()
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(self.topic_posts_delete_url)
        for _ in range(post_count):
            message = await communicator.receive_from()
            assert "post_deleted" in message
        await communicator.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_board_posts_deleted_websocket_message(self, client, board, user):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        post_count = await Post.objects.filter(topic__board=board).acount()
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(self.board_posts_delete_url)
        for _ in range(post_count):
            message = await communicator.receive_from()
            assert "post_deleted" in message
        await communicator.disconnect()


class TestPostFetchView:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, board, topic, post):
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
        assert response.status_code == 200
        assert response.context["post"] == post
        assertContains(response, post.content, html=True)

    def test_post_fetch_approved(self, client, board, post):
        board.preferences.require_post_approval = True
        board.preferences.save()
        post.approved = True
        post.save()
        response = client.get(self.post_fetch_url)
        assert response.status_code == 200
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
        assert response.status_code == 204
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
        assert response.status_code == 204
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
    def setup_method_fixture(self, board, topic, post, user, reaction_factory):
        board.preferences.reaction_type = "l"
        board.preferences.save()
        for type in REACTION_TYPE[1:]:
            reaction_factory(post=post, type=type[0], user=user)
        self.post_footer_fetch_url = reverse(
            "boards:post-footer-fetch",
            kwargs={"slug": board.slug, "topic_pk": topic.pk, "pk": post.pk},
        )

    def test_post_footer_fetch_anonymous(self, client, post):
        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            if type == "l":
                icon = "bi-heart"
            elif type == "v":
                icon = "bi-hand-thumbs-up"
            elif type == "s":
                icon = "bi-star"

            post.topic.board.preferences.reaction_type = type
            post.topic.board.preferences.save()
            post.approved = False
            post.save()

            response = client.get(self.post_footer_fetch_url)
            assert response.status_code == 200
            assert response.context["post"] == post
            assertNotContains(response, icon)

            post.approved = True
            post.save()
            response = client.get(self.post_footer_fetch_url)
            assert response.status_code == 200
            assert response.context["post"] == post
            assertContains(response, icon)

    def test_post_footer_fetch_moderator(self, client, post, user3):
        client.force_login(user3)
        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            if type == "l":
                icon = "bi-heart"
            elif type == "v":
                icon = "bi-hand-thumbs-up"
            elif type == "s":
                icon = "bi-star"

            post.topic.board.preferences.reaction_type = type
            post.topic.board.preferences.save()
            post.approved = False
            post.save()

            response = client.get(self.post_footer_fetch_url)
            assert response.status_code == 200
            assert response.context["post"] == post
            assertContains(response, icon)

            post.approved = True
            post.save()
            response = client.get(self.post_footer_fetch_url)
            assert response.status_code == 200
            assert response.context["post"] == post
            assertContains(response, icon)


class TestPostToggleApprovalView:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, board, topic, post):
        board.preferences.require_post_approval = True
        board.preferences.save()
        post.approved = False
        post.save()
        self.post_approval_url = reverse(
            "boards:post-toggle-approval",
            kwargs={"slug": board.slug, "topic_pk": topic.pk, "pk": post.pk},
        )

    def test_post_toggle_approval_anonymous(self, client, post):
        assert not post.approved
        response = client.post(self.post_approval_url)
        assert response.status_code == 302
        post.refresh_from_db()
        assert not post.approved

    def test_post_toggle_approval_other_user(self, client, post, user2):
        client.force_login(user2)
        assert not post.approved
        response = client.post(self.post_approval_url)
        assert response.status_code == 403
        post.refresh_from_db()
        assert not post.approved

    @pytest.mark.parametrize(
        "test_user",
        [
            lazy_fixture("user"),
            lazy_fixture("user3"),
            lazy_fixture("user_staff"),
        ],
    )
    def test_post_toggle_approval_authorized_user(self, client, post, test_user):
        client.force_login(test_user)
        assert not post.approved
        response = client.post(self.post_approval_url)
        assert response.status_code == 204
        post.refresh_from_db()
        assert post.approved
        response = client.post(self.post_approval_url)
        assert response.status_code == 204
        post.refresh_from_db()
        assert not post.approved

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_post_toggle_websocket_message(self, client, board, post, user):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(self.post_approval_url)
        message = await communicator.receive_from()
        assert "post_updated" in message
        assert f'"post_pk": "{str(post.pk)}"' in message
        await sync_to_async(client.post)(self.post_approval_url)
        message = await communicator.receive_from()
        assert "post_updated" in message
        assert f'"post_pk": "{str(post.pk)}"' in message
        await communicator.disconnect()


class TestPostImageUploadView:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, board):
        board.preferences.allow_image_uploads = True
        board.preferences.save()
        self.upload_url = reverse("boards:post-image-upload", kwargs={"slug": board.slug})

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_permissions(self, client, board):
        response = client.get(self.upload_url)
        assert response.status_code == 405

        valid_image_types = ["image/png", "image/jpeg", "image/bmp", "image/webp"]
        for image_type in valid_image_types:
            response = client.post(
                self.upload_url,
                {
                    "image": SimpleUploadedFile(
                        "test.png",
                        create_image(image_type.split("/")[1]),
                        content_type=image_type,
                    )
                },
            )
            assert response.status_code == 200
            image = Image.objects.order_by("created_at").last()
            data = json.loads(response.content)
            assert data["data"]["filePath"] == image.image.url

        board.preferences.allow_image_uploads = False
        board.preferences.save()

        response = client.post(self.upload_url)
        assert response.status_code == 302

    def test_upload_image_over_max_count(self, client):
        for i in range(settings.MAX_POST_IMAGE_COUNT + 1):
            response = client.post(
                self.upload_url,
                {"image": SimpleUploadedFile(f"test{i}.png", create_image("png"), content_type="image/png")},
            )
            data = json.loads(response.content)
            if i < settings.MAX_POST_IMAGE_COUNT:
                assert data["data"]["filePath"] == Image.objects.order_by("created_at").last().image.url
            else:
                assert data["error"] == "Board image quota exceeded"

    def test_upload_invalid_image(self, client):
        response = client.post(
            self.upload_url,
            {"image": SimpleUploadedFile("test.avif", create_image("avif"), content_type="image/avif")},
        )
        data = json.loads(response.content)
        assert data["error"] == "Invalid image type (only PNG, JPEG, GIF, BMP, and WEBP are allowed)"
