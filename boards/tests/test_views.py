import json
import os
import shutil
import tempfile

import factory
from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from django_htmx.middleware import HtmxMiddleware

from accounts.tests.factories import USER_TEST_PASSWORD, UserFactory
from boards.models import IMAGE_TYPE, REACTION_TYPE, Board, BoardPreferences, Image, Post, Reaction, Topic
from boards.routing import websocket_urlpatterns
from boards.views import BoardView

from .factories import BoardFactory, ImageFactory, PostFactory, ReactionFactory, TopicFactory

MEDIA_ROOT = tempfile.mkdtemp()
module_dir = os.path.dirname(__file__)


def create_image(type):
    return factory.Faker("image", image_format=type).evaluate({}, None, {"locale": "en"})


def dummy_request(request):
    return HttpResponse("Hello!")


class IndexViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = UserFactory()
        cls.board = BoardFactory(owner=test_user1)

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:index"))
        self.assertEqual(response.status_code, 200)

    def test_board_search_success(self):
        response = self.client.post(reverse("boards:index"), {"board_slug": self.board.slug})
        self.assertEqual(response.status_code, 302)

    def test_board_search_invalid(self):
        response = self.client.post(reverse("boards:index"), {"board_slug": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "board_slug", "ID should be 6 or 8 lowercase letters and/or digits."
        )

    def test_board_search_not_found(self):
        bad_slug = "000000" if self.board.slug != "000000" else "111111"
        response = self.client.post(reverse("boards:index"), {"board_slug": bad_slug})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "board_slug", "Board does not exist.")

    def test_board_search_no_slug(self):
        response = self.client.post(reverse("boards:index"))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "board_slug", "This field is required.")


class IndexAllBoardsViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = UserFactory()
        cls.user2 = UserFactory(is_staff=True)

    def test_anonymous_all_boards(self):
        response = self.client.get(reverse("boards:index-all"))
        self.assertEqual(response.status_code, 302)

    def test_board_non_staff_all_boards(self):
        self.client.login(username=self.user1.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:index-all"))
        self.assertEqual(response.status_code, 403)

    def test_board_staff_all_boards(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:index-all"))
        self.assertEqual(response.status_code, 200)


class BoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.board = BoardFactory(owner=cls.user, slug="000001")

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.htmx_middleware = HtmxMiddleware(dummy_request)

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:board", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_board_not_exist(self):
        response = self.client.get(reverse("boards:board", kwargs={"slug": "000000"}))
        self.assertEqual(response.status_code, 404)

    def test_htmx_requests(self):
        kwargs = {"slug": self.board.slug}

        # request with no current_url
        request = self.factory.get(reverse("boards:board", kwargs=kwargs), HTTP_HX_REQUEST="true")
        session_middleware = SessionMiddleware(request)
        session_middleware.process_request(request)
        request.session.save()
        request.user = self.user
        self.htmx_middleware(request)

        response = BoardView.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "boards/board_index.html")

        # request from index
        request = self.factory.get(
            reverse("boards:board", kwargs=kwargs),
            HTTP_HX_REQUEST="true",
            HTTP_HX_CURRENT_URL=reverse("boards:index"),
        )
        session_middleware = SessionMiddleware(request)
        session_middleware.process_request(request)
        request.session.save()
        request.user = self.user
        self.htmx_middleware(request)

        response = BoardView.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "boards/board_index.html")

        # request from index-all
        request = self.factory.get(
            reverse("boards:board", kwargs=kwargs),
            HTTP_HX_REQUEST="true",
            HTTP_HX_CURRENT_URL=reverse("boards:index-all"),
        )
        session_middleware = SessionMiddleware(request)
        session_middleware.process_request(request)
        request.session.save()
        request.user = self.user
        self.htmx_middleware(request)

        response = BoardView.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "boards/board_index.html")

        # request from board URL
        request = self.factory.get(
            reverse("boards:board", kwargs=kwargs),
            HTTP_HX_REQUEST="true",
            HTTP_HX_CURRENT_URL=reverse("boards:board", kwargs=kwargs),
        )
        session_middleware = SessionMiddleware(request)
        session_middleware.process_request(request)
        request.session.save()
        request.user = self.user
        self.htmx_middleware(request)

        response = BoardView.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "boards/components/board.html")

        # request from another board URL
        request = self.factory.get(
            reverse("boards:board", kwargs=kwargs),
            HTTP_HX_REQUEST="true",
            HTTP_HX_CURRENT_URL=reverse("boards:board", kwargs={"slug": "000000"}),
        )
        session_middleware = SessionMiddleware(request)
        session_middleware.process_request(request)
        request.session.save()
        request.user = self.user
        self.htmx_middleware(request)

        response = BoardView.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "boards/board_index.html")


class BoardPreferencesViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board_preferences_changed_url = reverse("boards:board-preferences", kwargs={"slug": cls.board.slug})

    def test_board_preferences_anonymous_permissions(self):
        response = self.client.get(reverse("boards:board-preferences", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/accounts/login/?next=/boards/{self.board.slug}/preferences/")

    def test_board_references_other_user_permissions(self):
        self.client.login(username=self.user2, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-preferences", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_board_preferences_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-preferences", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_board_preferences_nonexistent_preferences(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        preferences_pk = self.board.preferences.pk
        self.board.preferences.delete()
        self.assertRaises(BoardPreferences.DoesNotExist, BoardPreferences.objects.get, pk=preferences_pk)
        response = self.client.get(reverse("boards:board-preferences", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)
        preferences = BoardPreferences.objects.get(board=self.board)
        self.assertEqual(preferences.board, self.board)

    async def test_preferences_changed_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        response = await sync_to_async(self.client.post)(
            self.board_preferences_changed_url,
            data={
                "type": "d",
                "background_type": "c",
                "background_color": "#ffffff",
                "background_image": "",
                "background_opacity": "0.5",
                "require_post_approval": True,
                "allow_guest_replies": True,
                "enable_latex": True,
                "reaction_type": "v",
            },
        )
        message = await communicator.receive_from()
        self.assertIn("board_preferences_changed", message)
        self.assertEqual(response.status_code, 204)


class CreateBoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:board-create"))
        self.assertEqual(response.status_code, 302)

    def test_user_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-create"))
        self.assertEqual(str(response.context["user"]), self.user.username)
        self.assertEqual(response.status_code, 200)

    def test_board_create_success(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:board-create"), {"title": "Test Board", "description": "Test Board Description"}
        )
        self.assertEqual(response.status_code, 200)
        board = Board.objects.get(title="Test Board")
        self.assertEqual(board.description, "Test Board Description")

    def test_board_create_blank(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(reverse("boards:board-create"), {"title": "", "description": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "title", "This field is required.")
        self.assertFormError(response.context["form"], "description", "This field is required.")

    def test_board_create_invalid(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(reverse("boards:board-create"), {"title": "x" * 51, "description": "x" * 101})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "title", "Ensure this value has at most 50 characters (it has 51)."
        )
        self.assertFormError(
            response.context["form"], "description", "Ensure this value has at most 100 characters (it has 101)."
        )


class UpdateBoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_staff_permissions(self):
        staff_user = UserFactory(is_staff=True)
        self.client.login(username=staff_user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_board_update_success(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:board-update", kwargs={"slug": self.board.slug}),
            {"title": "Test Board NEW", "description": "Test Board Description NEW"},
        )
        self.assertEqual(response.status_code, 200)
        self.board = Board.objects.get(pk=self.board.pk)
        self.assertEqual(self.board.title, "Test Board NEW")
        self.assertEqual(self.board.description, "Test Board Description NEW")

    def test_board_update_blank(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:board-update", kwargs={"slug": self.board.slug}),
            {"title": "", "description": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "title", "This field is required.")
        self.assertFormError(response.context["form"], "description", "This field is required.")

    def test_board_update_invalid(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:board-update", kwargs={"slug": self.board.slug}),
            {"title": "x" * 51, "description": "x" * 101},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "title",
            "Ensure this value has at most 50 characters (it has 51).",
        )
        self.assertFormError(
            response.context["form"],
            "description",
            "Ensure this value has at most 100 characters (it has 101).",
        )


class DeleteBoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:board-delete", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Board.objects.all()), 0)

    def test_staff_permissions(self):
        staff_user = UserFactory(is_staff=True)
        self.client.login(username=staff_user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:board-delete", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Board.objects.all()), 0)

    def test_delete_board_with_reactions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        topic = TopicFactory(board=self.board)
        post = PostFactory(topic=topic)
        ReactionFactory(post=post)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:board-delete", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Board.objects.all()), 0)


class TopicCreateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.topic_created_url = reverse("boards:topic-create", kwargs={"slug": cls.board.slug})

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_staff_permissions(self):
        staff_user = UserFactory(is_staff=True)
        self.client.login(username=staff_user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_topic_create_success(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:topic-create", kwargs={"slug": self.board.slug}),
            data={"subject": "Test Topic"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertIsNotNone(Topic.objects.get(subject="Test Topic"))

    def test_topic_create_blank(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:topic-create", kwargs={"slug": self.board.slug}),
            data={"subject": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "subject", "This field is required.")

    def test_topic_create_invalid(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:topic-create", kwargs={"slug": self.board.slug}),
            data={"subject": "x" * 401},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "subject", "Ensure this value has at most 400 characters (it has 401)."
        )

    async def test_topic_created_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.topic_created_url, data={"subject": "Test Topic"})
        topic = await sync_to_async(Topic.objects.get)(subject="Test Topic")
        message = await communicator.receive_from()
        self.assertIn("topic_created", message)
        self.assertIn(f'"topic_pk": {topic.id}', message)


class TopicUpdateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.topic = TopicFactory(board=cls.board)
        cls.topic_updated_url = reverse("boards:topic-update", kwargs={"slug": cls.board.slug, "pk": cls.topic.pk})

    def test_anonymous_permissions(self):
        response = self.client.get(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_staff_permissions(self):
        staff_user = UserFactory(is_staff=True)
        self.client.login(username=staff_user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_topic_update_success(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk}),
            data={"subject": "Test Topic NEW"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertIsNotNone(Topic.objects.get(subject="Test Topic NEW"))

    def test_topic_update_blank(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk}),
            data={"subject": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "subject", "This field is required.")

    def test_topic_update_invalid(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk}),
            data={"subject": "x" * 401},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "subject", "Ensure this value has at most 400 characters (it has 401)."
        )

    async def test_topic_updated_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.topic_updated_url, data={"subject": "Test Topic NEW"})
        message = await communicator.receive_from()
        self.assertIn("topic_updated", message)
        self.assertIn(f'"topic_pk": {self.topic.pk}', message)


class TopicDeleteViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.topic = TopicFactory(board=cls.board)
        cls.topic_deleted_url = reverse("boards:topic-delete", kwargs={"slug": cls.board.slug, "pk": cls.topic.pk})

    def test_anonymous_permissions(self):
        response = self.client.get(
            reverse("boards:topic-delete", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:topic-delete", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:topic-delete", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("boards:topic-delete", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertRaises(Topic.DoesNotExist, Topic.objects.get, pk=self.topic.pk)
        self.assertEqual(response.status_code, 204)

    def test_staff_permissions(self):
        staff_user = UserFactory(is_staff=True)
        self.client.login(username=staff_user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:topic-delete", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("boards:topic-delete", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertRaises(Topic.DoesNotExist, Topic.objects.get, pk=self.topic.pk)
        self.assertEqual(response.status_code, 204)

    async def test_topic_deleted_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.topic_deleted_url)
        message = await communicator.receive_from()
        self.assertIn("topic_deleted", message)
        self.assertIn(f'"topic_pk": {self.topic.pk}', message)


class DeleteTopicPostsViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.topic = TopicFactory(board=cls.board)
        cls.topic_posts_delete_url = reverse(
            "boards:topic-posts-delete", kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk}
        )
        PostFactory.create_batch(10, topic=cls.topic, user=cls.user)

    def test_anonymous_permissions(self):
        response = self.client.get(
            reverse("boards:topic-posts-delete", kwargs={"slug": self.topic.board.slug, "topic_pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        delete_url = reverse(
            "boards:topic-posts-delete", kwargs={"slug": self.topic.board.slug, "topic_pk": self.topic.pk}
        )
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.filter(topic=self.topic).count(), 10)

        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.filter(topic=self.topic).count(), 0)

    async def test_topic_posts_deleted_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.topic_posts_delete_url)
        for _ in range(10):
            message = await communicator.receive_from()
            self.assertIn("post_deleted", message)


class PostCreateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        cls.post_create_url = reverse("boards:post-create", kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk})

    def test_anonymous_permissions(self):
        post_url = reverse("boards:post-create", kwargs={"slug": self.topic.board.slug, "topic_pk": self.topic.pk})
        response = self.client.get(post_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(post_url, data={"content": "Test Message anon"})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.first().content, "Test Message anon")

    def test_replies_permissions_anonymous(self):
        post = PostFactory(topic=self.topic)
        reply_url = reverse(
            "boards:post-reply",
            kwargs={"slug": self.topic.board.slug, "topic_pk": self.topic.pk, "post_pk": post.pk},
        )
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 302)

        self.topic.board.preferences.type = "r"
        self.topic.board.preferences.save()
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 302)

        self.topic.board.preferences.allow_guest_replies = True
        self.topic.board.preferences.save()
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 200)

        post.approved = False
        post.save()
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 302)

    def test_replies_permissions_owner(self):
        post = PostFactory(topic=self.topic)
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        reply_url = reverse(
            "boards:post-reply",
            kwargs={"slug": self.topic.board.slug, "topic_pk": self.topic.pk, "post_pk": post.pk},
        )
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 403)

        self.topic.board.preferences.type = "r"
        self.topic.board.preferences.save()
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 200)

        post.approved = False
        post.save()
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 200)

    def test_reply(self):
        post = PostFactory(topic=self.topic)
        reply_url = reverse(
            "boards:post-reply",
            kwargs={"slug": self.topic.board.slug, "topic_pk": self.topic.pk, "post_pk": post.pk},
        )
        self.topic.board.preferences.type = "r"
        self.topic.board.preferences.allow_guest_replies = True
        self.topic.board.preferences.save()

        self.client.post(reply_url, data={"content": "Test Message reply"})
        reply = Post.objects.get(content="Test Message reply")
        self.assertEqual(reply.topic, self.topic)
        self.assertEqual(reply.reply_to, post)

    def test_post_session_key(self):
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": self.topic.board.slug, "topic_pk": self.topic.pk}),
            data={"content": "Test Post"},
        )
        self.assertEqual(self.client.session.session_key, Post.objects.get(content="Test Post").session_key)

    def test_post_approval(self):
        self.board.preferences.require_post_approval = True
        self.board.preferences.save()
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk}),
            data={"content": "Test Post"},
        )
        self.assertEqual(Post.objects.get(content="Test Post").approved, False)

        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk}),
            data={"content": "Test Post user1"},
        )
        self.assertEqual(
            Post.objects.get(content="Test Post user1").approved, True
        )  # Board owner can post without approval

        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk}),
            data={"content": "Test Post user2"},
        )
        self.assertEqual(Post.objects.get(content="Test Post user2").approved, False)  # Normal user needs approval

        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk}),
            data={"content": "Test Post user3"},
        )
        self.assertEqual(
            Post.objects.get(content="Test Post user3").approved, True
        )  # Moderator can post without approval

    async def test_post_created_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.post_create_url, data={"content": "Test Post"})
        post = await sync_to_async(Post.objects.get)(content="Test Post")
        self.assertIsNotNone(post)
        message = await communicator.receive_from()
        self.assertIn("post_created", message)
        self.assertIn(f'"topic_pk": {self.topic.pk}', message)


class PostUpdateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        cls.post = PostFactory(topic=cls.topic)
        cls.post_updated_url = reverse(
            "boards:post-update", kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk}
        )

    def test_anonymous_permissions(self):
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk}),
            data={"content": "Test Post anon"},
        )
        post = Post.objects.get(content="Test Post anon")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.session.session_key, post.session_key)
        response = self.client.post(
            reverse("boards:post-update", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": post.pk}),
            data={"content": "Test Post anon NEW"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.get(pk=post.pk).content, "Test Post anon NEW")

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse(
                "boards:post-update", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_board_moderator_permissions(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse(
                "boards:post-update", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            )
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse(
                "boards:post-update", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            ),
            data={"content": "Test Post NEW"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.get(pk=self.post.pk).content, "Test Post NEW")

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse(
                "boards:post-update", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            )
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse(
                "boards:post-update", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            ),
            data={"content": "Test Post NEW"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.get(pk=self.post.pk).content, "Test Post NEW")

    async def test_post_updated_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.post_updated_url, data={"content": "Test Post NEW"})
        message = await communicator.receive_from()
        self.assertIn("post_updated", message)
        self.assertIn(f'"post_pk": {self.post.pk}', message)


class PostDeleteViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        cls.post = PostFactory(topic=cls.topic)
        cls.post_deleted_url = reverse(
            "boards:post-delete", kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk}
        )

    def test_anonymous_permissions(self):
        self.client.post(
            reverse(
                "boards:post-delete", kwargs={"slug": "test-board", "topic_pk": self.topic.pk, "pk": self.post.pk}
            )
        )
        self.assertEqual(Post.objects.count(), 1)
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": "test-board", "topic_pk": self.topic.pk}),
            data={"content": "Test Post anon"},
        )
        post2 = Post.objects.get(content="Test Post anon")
        self.assertEqual(Post.objects.count(), 2)
        self.client.post(
            reverse("boards:post-delete", kwargs={"slug": "test-board", "topic_pk": self.topic.pk, "pk": post2.pk})
        )
        self.assertEqual(Post.objects.count(), 1)

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse(
                "boards:post-delete", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Post.objects.count(), 1)

    def test_board_moderator_permissions(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse(
                "boards:post-delete", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            )
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.count(), 0)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse(
                "boards:post-delete", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            )
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.count(), 0)

    async def test_post_deleted_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.post_deleted_url)
        message = await communicator.receive_from()
        self.assertIn("post_deleted", message)
        self.assertIn(f'"post_pk": {self.post.pk}', message)


class ReactionsDeleteViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.reaction_type = "l"
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        PostFactory.create_batch(5, topic=cls.topic)
        for post in Post.objects.all():
            for type in REACTION_TYPE[1:]:
                ReactionFactory.create_batch(
                    5,
                    post=post,
                    type=type[0],
                    reaction_score="1",
                )
        cls.post = Post.objects.first()
        cls.reactions_delete_url = reverse(
            "boards:post-reactions-delete",
            kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk},
        )

    def test_anonymous_permissions(self):
        response = self.client.get(self.reactions_delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

        response = self.client.post(self.reactions_delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.reactions_delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

        response = self.client.post(self.reactions_delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

    def test_moderator_permissions(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.reactions_delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

        response = self.client.post(self.reactions_delete_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1) - 5)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.reactions_delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

        response = self.client.post(self.reactions_delete_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1) - 5)

    def test_no_reactions_preferences(self):
        self.board.preferences.reaction_type = "n"
        self.board.preferences.save()
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.reactions_delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

        response = self.client.post(self.reactions_delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

    async def test_post_toggle_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.reactions_delete_url)
        message = await communicator.receive_from()
        self.assertIn("reaction_updated", message)
        self.assertIn(f'"post_pk": {self.post.pk}', message)


# TODO: Implement further tests for all board_list_types
class BoardListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        BoardFactory.create_batch(3, owner=cls.user)
        BoardFactory.create_batch(3, owner=cls.user2)

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:board-list", kwargs={"board_list_type": "own"}))
        self.assertEqual(response.status_code, 302)

    def test_user_index(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:board-list", kwargs={"board_list_type": "own"}), {}, HTTP_REFERER=reverse("boards:index")
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "boards/components/board_list.html")
        self.assertEqual(len(response.context["boards"]), 3)

    def test_user_no_perm_all_boards(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:board-list", kwargs={"board_list_type": "own"}),
            {},
            HTTP_REFERER=reverse("boards:index-all"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "boards/components/board_list.html")
        self.assertEqual(len(response.context["boards"]), 3)

    def test_user_perm_all_boards(self):
        self.user.user_permissions.add(Permission.objects.get(codename="can_view_all_boards"))
        self.user.save()
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:board-list", kwargs={"board_list_type": "all"}),
            {},
            HTTP_REFERER=reverse("boards:index-all"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "boards/components/board_list.html")
        self.assertEqual(len(response.context["boards"]), 5)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertEqual(len(response.context["page_obj"].paginator.page_range), 2)

    def test_user_perm_second_page(self):
        self.user.user_permissions.add(Permission.objects.get(codename="can_view_all_boards"))
        self.user.save()
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:board-list", kwargs={"board_list_type": "all"}),
            {"page": 2},
            HTTP_REFERER=reverse("boards:index-all"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "boards/components/board_list.html")
        self.assertEqual(len(response.context["boards"]), 1)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["page_obj"].paginator.page_range), 2)


class TopicFetchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.topic = TopicFactory()

    def test_topic_fetch(self):
        response = self.client.get(
            reverse("boards:topic-fetch", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["topic"], self.topic)


class PostFetchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.require_post_approval = True
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        cls.post = PostFactory(topic=cls.topic, approved=False)
        cls.post_fetch_url = reverse(
            "boards:post-fetch", kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk}
        )

    def test_post_fetch_require_no_approval(self):
        self.board.preferences.require_post_approval = False
        self.board.preferences.save()
        response = self.client.get(self.post_fetch_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["post"], self.post)
        self.assertContains(response, self.post.content, html=True)

    def test_post_fetch_approved(self):
        self.board.preferences.require_post_approval = True
        self.board.preferences.save()
        self.post.approved = True
        self.post.save()
        response = self.client.get(self.post_fetch_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["post"], self.post)
        self.assertContains(response, self.post.content, html=True)

    def test_post_fetch_content_anonymous_not_approved(self):
        self.client.get(reverse("boards:board", kwargs={"slug": self.board.slug}))
        response = self.client.get(self.post_fetch_url)
        self.assertNotContains(response, self.post.content, html=True)

    def test_post_fetch_content_anonymous_not_approved_own_post(self):
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk}),
            data={"content": "Test Post anon"},
        )
        post = Post.objects.get(content="Test Post anon")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": post.pk})
        )
        self.assertContains(response, post.content, html=True)

    def test_post_fetch_content_other_user_not_approved(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        self.client.get(reverse("boards:board", kwargs={"slug": self.board.slug}))

        response = self.client.get(self.post_fetch_url)
        self.assertNotContains(response, self.post.content, html=True)

    def test_post_fetch_content_other_user_not_approved_own_post(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk}),
            data={"content": "Test Post anon"},
        )
        post = Post.objects.get(content="Test Post anon")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": post.pk})
        )
        self.assertContains(response, post.content, html=True)

    def test_post_fetch_content_board_moderator_not_approved(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.post_fetch_url)
        self.assertContains(response, self.post.content, html=True)

    def test_post_fetch_content_owner_not_approved(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.post_fetch_url)
        self.assertContains(response, self.post.content, html=True)

    def test_post_fetch_content_can_approve_not_approved(self):
        user4 = UserFactory()
        user4.user_permissions.add(Permission.objects.get(codename="can_approve_posts"))
        self.client.login(username=user4.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.post_fetch_url)
        self.assertContains(response, self.post.content, html=True)


class PostFooterFetchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.reaction_type = "l"
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        cls.post = PostFactory(topic=cls.topic, approved=True)
        for type in REACTION_TYPE[1:]:
            ReactionFactory(post=cls.post, type=type[0], user=cls.user)
        cls.post_footer_fetch_url = reverse(
            "boards:post-footer-fetch",
            kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk},
        )

    def test_post_footer_fetch_anonymous(self):
        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            if type == "l":
                icon = "bi-heart"
            elif type == "v":
                icon = "bi-hand-thumbs-up"
            elif type == "s":
                icon = "bi-star"

            self.post.topic.board.preferences.reaction_type = type
            self.post.topic.board.preferences.save()
            self.post.approved = False
            self.post.save()

            response = self.client.get(self.post_footer_fetch_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["post"], self.post)
            self.assertNotContains(response, icon)

            self.post.approved = True
            self.post.save()
            response = self.client.get(self.post_footer_fetch_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["post"], self.post)
            self.assertContains(response, icon)

    def test_post_footer_fetch_moderator(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        post = Post.objects.get(pk=self.post.pk)
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

            response = self.client.get(self.post_footer_fetch_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["post"], post)
            self.assertContains(response, icon)

            post.approved = True
            post.save()
            response = self.client.get(self.post_footer_fetch_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["post"], post)
            self.assertContains(response, icon)


class PostToggleApprovalViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.require_post_approval = True
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        cls.post = PostFactory(topic=cls.topic, approved=False)
        cls.post_approval_url = reverse(
            "boards:post-toggle-approval",
            kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk},
        )

    def test_post_toggle_approval_anonymous(self):
        self.assertFalse(self.post.approved)
        response = self.client.post(self.post_approval_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Post.objects.get(pk=self.post.pk).approved)

    def test_post_toggle_approval_other_user(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        self.assertFalse(self.post.approved)
        response = self.client.post(self.post_approval_url)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Post.objects.get(pk=self.post.pk).approved)

    def test_post_toggle_approval_board_moderator(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        self.assertFalse(self.post.approved)
        response = self.client.post(self.post_approval_url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Post.objects.get(pk=self.post.pk).approved)
        response = self.client.post(self.post_approval_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Post.objects.get(pk=self.post.pk).approved)

    def test_post_toggle_approval_owner(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        self.assertFalse(self.post.approved)
        response = self.client.post(self.post_approval_url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Post.objects.get(pk=self.post.pk).approved)
        response = self.client.post(self.post_approval_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Post.objects.get(pk=self.post.pk).approved)

    async def test_post_toggle_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.post_approval_url)
        message = await communicator.receive_from()
        self.assertIn("post_updated", message)
        self.assertIn(f'"post_pk": {self.post.pk}', message)
        await sync_to_async(self.client.post)(self.post_approval_url)
        message = await communicator.receive_from()
        self.assertIn("post_updated", message)
        self.assertIn(f'"post_pk": {self.post.pk}', message)


class PostReactionViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.topic = TopicFactory(board=cls.board)
        cls.post = PostFactory(topic=cls.topic, user=cls.user)
        cls.post_reaction_url = reverse(
            "boards:post-reaction", kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk}
        )

    def test_post_reaction_repeat_anonymous(self):
        self.assertEqual(Reaction.objects.count(), 0)

        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            self.post.topic.board.preferences.reaction_type = type
            self.post.topic.board.preferences.save()

            response = self.client.post(self.post_reaction_url, {"score": 1})
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 1)

            response = self.client.post(self.post_reaction_url, {"score": 1})
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 0)

    def test_post_reaction_score_changed(self):
        self.assertEqual(Reaction.objects.count(), 0)

        for _type in REACTION_TYPE[2:]:  # like only has one score
            type = _type[0]
            self.post.topic.board.preferences.reaction_type = type
            self.post.topic.board.preferences.save()
            if type == "v":
                second_score = -1
            elif type == "s":
                second_score = 2

            response = self.client.post(self.post_reaction_url, {"score": 1})
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 1)
            self.assertEqual(Reaction.objects.first().reaction_score, 1)

            response = self.client.post(self.post_reaction_url, {"score": second_score})
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 1)
            self.assertEqual(Reaction.objects.first().reaction_score, second_score)

            Reaction.objects.filter(post=self.post).delete()

    def test_post_reaction_disabled(self):
        self.assertEqual(Reaction.objects.count(), 0)

        response = self.client.post(self.post_reaction_url, {"score": 1})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Reaction.objects.count(), 0)

    def test_post_reaction_own_post(self):
        self.assertEqual(Reaction.objects.count(), 0)

        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)

        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            self.post.topic.board.preferences.reaction_type = type
            self.post.topic.board.preferences.save()

            response = self.client.post(
                self.post_reaction_url,
                {"score": 1},
            )
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 0)

    async def test_reaction_updated_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            preferences = await sync_to_async(BoardPreferences.objects.get)(board=self.board)
            preferences.reaction_type = type
            await sync_to_async(preferences.save)()
            message = await communicator.receive_from()
            self.assertIn("board_preferences_changed", message)
            await sync_to_async(self.client.post)(self.post_reaction_url, data={"score": 1})
            message = await communicator.receive_from()
            self.assertIn("reaction_updated", message)
            self.assertIn(f'"post_pk": {self.post.pk}', message)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PostImageUploadViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.board = BoardFactory()
        cls.board.preferences.allow_image_uploads = True
        cls.board.preferences.save()
        cls.upload_url = reverse("boards:post-image-upload", kwargs={"slug": cls.board.slug})

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_permissions(self):
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, 405)

        valid_image_types = ["image/png", "image/jpeg", "image/bmp", "image/webp"]
        for image_type in valid_image_types:
            response = self.client.post(
                self.upload_url,
                {
                    "image": SimpleUploadedFile(
                        "test.png",
                        create_image(image_type.split("/")[1]),
                        content_type=image_type,
                    )
                },
            )
            self.assertEqual(response.status_code, 200)
            image = Image.objects.order_by("created_at").last()
            data = json.loads(response.content)
            self.assertEqual(data["data"]["filePath"], image.image.url)

        self.board.preferences.allow_image_uploads = False
        self.board.preferences.save()

        response = self.client.post(self.upload_url)
        self.assertEqual(response.status_code, 302)

    def test_upload_image_over_max_count(self):
        for i in range(settings.MAX_POST_IMAGE_COUNT + 1):
            response = self.client.post(
                self.upload_url,
                {"image": SimpleUploadedFile(f"test{i}.png", create_image("png"), content_type="image/png")},
            )
            data = json.loads(response.content)
            if i < settings.MAX_POST_IMAGE_COUNT:
                self.assertEqual(data["data"]["filePath"], Image.objects.order_by("created_at").last().image.url)
            else:
                self.assertEqual(data["error"], "Board image quota exceeded")

    def test_upload_invalid_image(self):
        response = self.client.post(
            self.upload_url,
            {"image": SimpleUploadedFile("test.avif", create_image("avif"), content_type="image/avif")},
        )
        data = json.loads(response.content)
        self.assertEqual(data["error"], "Invalid image type (only PNG, JPEG, GIF, BMP, and WEBP are allowed)")


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ImageSelectViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.board = BoardFactory()
        for type, text in IMAGE_TYPE:
            ImageFactory.create_batch(5, board=cls.board if type == "p" else None, type=type)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_image_select_anonymous(self):
        for type, _ in IMAGE_TYPE:
            response = self.client.get(reverse("boards:image-select", kwargs={"type": type}))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, f"/accounts/login/?next=/boards/image_select/{type}/")

    def test_image_select_logged_in(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        for type, _ in IMAGE_TYPE:
            response = self.client.get(reverse("boards:image-select", kwargs={"type": type}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["images"].count(), Image.objects.filter(type=type).count())


class QrViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.save()

    def test_qr_anonymous(self):
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/accounts/login/?next=/boards/{self.board.slug}/qr/")

    def test_qr_other_user(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_qr_board_moderator(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("/qr_code/images/serve-qr-code-image/", response.content.decode("utf-8"))

    def test_qr_owner(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("/qr_code/images/serve-qr-code-image/", response.content.decode("utf-8"))

    def test_qr_staff(self):
        staff_user = UserFactory(is_staff=True)
        self.client.login(username=staff_user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)
