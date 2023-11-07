from http import HTTPStatus

import pytest
from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.urls import reverse
from pytest_django.asserts import assertFormError
from pytest_lazy_fixtures.lazy_fixture import lf

from boards.models import Topic
from boards.routing import websocket_urlpatterns


class TestTopicCreateView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board):
        self.topic_created_url = reverse("boards:topic-create", kwargs={"slug": board.slug})

    @pytest.mark.parametrize(
        ("test_user", "expected_response"),
        [
            (None, 302),
            (lf("user"), 200),
            (lf("user2"), 403),
            (lf("user_staff"), 200),
        ],
    )
    def test_permissions(self, client, board, test_user, expected_response):
        if test_user:
            client.force_login(test_user)
        response = client.get(reverse("boards:topic-create", kwargs={"slug": board.slug}))
        assert response.status_code == expected_response

    def test_topic_create_success(self, client, board, user):
        client.force_login(user)
        response = client.post(
            reverse("boards:topic-create", kwargs={"slug": board.slug}),
            data={"subject": "Test Topic"},
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Topic.objects.get(subject="Test Topic") is not None

    @pytest.mark.parametrize(
        ("subject", "expected_error"),
        [
            ("", "This field is required."),
            ("x" * 401, "Ensure this value has at most 400 characters (it has 401)."),
        ],
    )
    def test_topic_create_invalid(self, client, board, user, subject, expected_error):
        client.force_login(user)
        response = client.post(
            reverse("boards:topic-create", kwargs={"slug": board.slug}),
            data={"subject": subject},
        )
        assert response.status_code == HTTPStatus.OK
        assertFormError(response.context["form"], "subject", expected_error)

    @pytest.mark.asyncio()
    @pytest.mark.django_db(transaction=True)
    async def test_topic_created_websocket_message(self, client, board, user):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(self.topic_created_url, data={"subject": "Test Topic"})
        topic = await Topic.objects.aget(subject="Test Topic")
        message = await communicator.receive_from()
        assert "topic_created" in message
        assert f'"topic_pk": "{topic.pk!s}"' in message
        await communicator.disconnect()


class TestTopicUpdateView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, topic):
        self.topic_updated_url = reverse("boards:topic-update", kwargs={"slug": board.slug, "pk": topic.pk})

    @pytest.mark.parametrize(
        ("test_user", "expected_response"),
        [
            (None, 302),
            (lf("user"), 200),
            (lf("user2"), 403),
            (lf("user_staff"), 200),
        ],
    )
    def test_permissions(self, client, test_user, expected_response):
        if test_user:
            client.force_login(test_user)
        response = client.get(self.topic_updated_url)
        assert response.status_code == expected_response

    def test_topic_update_success(self, client, user):
        client.force_login(user)
        response = client.post(
            self.topic_updated_url,
            data={"subject": "Test Topic NEW"},
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Topic.objects.get(subject="Test Topic NEW") is not None

    @pytest.mark.parametrize(
        ("subject", "expected_error"),
        [
            ("", "This field is required."),
            ("x" * 401, "Ensure this value has at most 400 characters (it has 401)."),
        ],
    )
    def test_topic_update_invalid(self, client, user, subject, expected_error):
        client.force_login(user)
        response = client.post(
            self.topic_updated_url,
            data={"subject": subject},
        )
        assert response.status_code == HTTPStatus.OK
        assertFormError(response.context["form"], "subject", expected_error)

    @pytest.mark.asyncio()
    @pytest.mark.django_db(transaction=True)
    async def test_topic_updated_websocket_message(self, client, board, topic, user):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(self.topic_updated_url, data={"subject": "Test Topic NEW"})
        message = await communicator.receive_from()
        assert "topic_updated" in message
        assert f'"topic_pk": "{topic.pk!s}"' in message
        await communicator.disconnect()


class TestTopicDeleteView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, topic):
        self.topic_deleted_url = reverse("boards:topic-delete", kwargs={"slug": board.slug, "pk": topic.pk})

    @pytest.mark.parametrize(
        ("test_user", "expected_response"),
        [
            (None, HTTPStatus.FOUND),
            (lf("user"), HTTPStatus.OK),
            (lf("user2"), HTTPStatus.FORBIDDEN),
            (lf("user_staff"), HTTPStatus.OK),
        ],
    )
    def test_permissions(self, client, topic, test_user, expected_response):
        if test_user:
            client.force_login(test_user)
        response = client.get(self.topic_deleted_url)
        assert response.status_code == expected_response

        if expected_response == HTTPStatus.OK:
            response = client.post(self.topic_deleted_url)
            pytest.raises(Topic.DoesNotExist, Topic.objects.get, pk=topic.pk)
            assert response.status_code == HTTPStatus.NO_CONTENT

    @pytest.mark.asyncio()
    @pytest.mark.django_db(transaction=True)
    async def test_topic_deleted_websocket_message(self, client, board, topic, user):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(self.topic_deleted_url)
        message = await communicator.receive_from()
        assert "topic_deleted" in message
        assert f'"topic_pk": "{topic.pk!s}"' in message
        await communicator.disconnect()


class TestTopicFetchView:
    def test_topic_fetch(self, client, topic):
        response = client.get(reverse("boards:topic-fetch", kwargs={"slug": topic.board.slug, "pk": topic.pk}))
        assert response.status_code == HTTPStatus.OK
        assert response.context["topic"] == topic
