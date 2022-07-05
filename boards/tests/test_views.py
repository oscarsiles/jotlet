import os
import shutil
import tempfile

from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import Permission, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from django_htmx.middleware import HtmxMiddleware

from boards.models import IMAGE_TYPE, REACTION_TYPE, Board, BoardPreferences, Image, Post, Reaction, Topic
from boards.routing import websocket_urlpatterns
from boards.views import BoardView


def dummy_request(request):
    return HttpResponse("Hello!")


class IndexViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        Board.objects.create(title="Test Board", description="Test Board Description", owner=test_user1)

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:index"))
        self.assertEqual(response.status_code, 200)

    def test_board_search_success(self):
        board = Board.objects.get(title="Test Board")
        response = self.client.post(reverse("boards:index"), {"board_slug": board.slug})
        self.assertEqual(response.status_code, 302)

    def test_board_search_invalid(self):
        response = self.client.post(reverse("boards:index"), {"board_slug": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "board_slug", "ID format needs to be ######.")

    def test_board_search_not_found(self):
        board = Board.objects.get(title="Test Board")
        bad_slug = "000000" if board.slug != "000000" else "111111"
        response = self.client.post(reverse("boards:index"), {"board_slug": bad_slug})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "board_slug", "Board does not exist.")

    def test_board_search_no_slug(self):
        response = self.client.post(reverse("boards:index"))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "board_slug", "This field is required.")


class IndexAllBoardsViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="1X<ISRUkw+tuK", is_staff=True)

    def test_anonymous_all_boards(self):
        response = self.client.get(reverse("boards:index-all"))
        self.assertEqual(response.status_code, 302)

    def test_board_non_staff_all_boards(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("boards:index-all"))
        self.assertEqual(response.status_code, 403)

    def test_board_staff_all_boards(self):
        self.client.login(username="testuser2", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("boards:index-all"))
        self.assertEqual(response.status_code, 200)


class BoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        Board.objects.create(title="Test Board", description="Test Description", owner=test_user1, slug="000001")

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.htmx_middleware = HtmxMiddleware(dummy_request)

    def test_anonymous_permissions(self):
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_htmx_requests(self):
        board = Board.objects.get(title="Test Board")
        user = User.objects.get(username="testuser1")
        kwargs = {"slug": board.slug}

        # request with no current_url
        request = self.factory.get(reverse("boards:board", kwargs=kwargs), HTTP_HX_REQUEST="true")
        session_middleware = SessionMiddleware(request)
        session_middleware.process_request(request)
        request.session.save()
        request.user = user
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
        request.user = user
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
        request.user = user
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
        request.user = user
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
        request.user = user
        self.htmx_middleware(request)

        response = BoardView.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "boards/board_index.html")


class BoardPreferencesViewTest(TestCase):
    board_preferences_changed_url = ""

    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        cls.board_preferences_changed_url = reverse("boards:board-preferences", kwargs={"slug": board.slug})

    def test_board_preferences_anonymous_permissions(self):
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-preferences", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/accounts/login/?next=/boards/{board.slug}/preferences/")

    def test_board_references_other_user_permissions(self):
        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-preferences", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_board_preferences_owner_permissions(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-preferences", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_board_preferences_nonexistent_preferences(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        board.preferences.delete()
        self.assertRaises(BoardPreferences.DoesNotExist, BoardPreferences.objects.get, board=board)
        response = self.client.get(reverse("boards:board-preferences", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
        preferences = BoardPreferences.objects.get(board=board)
        self.assertEqual(preferences.board, board)

    async def test_preferences_changed_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board = await sync_to_async(Board.objects.get)(title="Test Board")
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username="testuser1", password="1X<ISRUkw+tuK")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        response = await sync_to_async(self.client.post)(
            self.board_preferences_changed_url,
            data={
                "background_type": "c",
                "background_color": "#ffffff",
                "background_image": "",
                "background_opacity": "0.5",
                "require_approval": True,
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
        User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:board-create"))
        self.assertEqual(response.status_code, 302)

    def test_user_permissions(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("boards:board-create"))
        self.assertEqual(str(response.context["user"]), "testuser1")
        self.assertEqual(response.status_code, 200)

    def test_board_create_success(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("boards:board-create"), {"title": "Test Board", "description": "Test Board Description"}
        )
        self.assertEqual(response.status_code, 200)
        board = Board.objects.get(title="Test Board")
        self.assertEqual(board.description, "Test Board Description")

    def test_board_create_blank(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(reverse("boards:board-create"), {"title": "", "description": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "title", "This field is required.")
        self.assertFormError(response, "form", "description", "This field is required.")

    def test_board_create_invalid(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(reverse("boards:board-create"), {"title": "x" * 51, "description": "x" * 101})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "title", "Ensure this value has at most 50 characters (it has 51).")
        self.assertFormError(
            response, "form", "description", "Ensure this value has at most 100 characters (it has 101)."
        )


class UpdateBoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)

    def test_anonymous_permissions(self):
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_staff_permissions(self):
        User.objects.create_user(username="staff", password="83jKJ+!fdjP", is_staff=True)
        self.client.login(username="staff", password="83jKJ+!fdjP")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_board_update_success(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        response = self.client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {"title": "Test Board NEW", "description": "Test Board Description NEW"},
        )
        self.assertEqual(response.status_code, 200)
        board = Board.objects.get(id=board.id)
        self.assertEqual(board.title, "Test Board NEW")
        self.assertEqual(board.description, "Test Board Description NEW")

    def test_board_update_blank(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        response = self.client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {"title": "", "description": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "title", "This field is required.")
        self.assertFormError(response, "form", "description", "This field is required.")

    def test_board_update_invalid(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        response = self.client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {"title": "x" * 51, "description": "x" * 101},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "title", "Ensure this value has at most 50 characters (it has 51).")
        self.assertFormError(
            response, "form", "description", "Ensure this value has at most 100 characters (it has 101)."
        )


class DeleteBoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)

    def test_anonymous_permissions(self):
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Board.objects.all()), 0)

    def test_staff_permissions(self):
        User.objects.create_user(username="staff", password="83jKJ+!fdjP", is_staff=True)
        self.client.login(username="staff", password="83jKJ+!fdjP")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Board.objects.all()), 0)

    def test_delete_board_with_reactions(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        topic = Topic.objects.create(subject="Test Topic", board=board)
        post = Post.objects.create(content="Test Post", topic=topic)
        Reaction.objects.create(post=post)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Board.objects.all()), 0)


class TopicCreateViewTest(TestCase):
    topic_created_url = ""

    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        cls.topic_created_url = reverse("boards:topic-create", kwargs={"slug": board.slug})

    def test_anonymous_permissions(self):
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_staff_permissions(self):
        User.objects.create_user(username="staff", password="83jKJ+!fdjP", is_staff=True)
        self.client.login(username="staff", password="83jKJ+!fdjP")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_topic_create_success(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        response = self.client.post(
            reverse("boards:topic-create", kwargs={"slug": board.slug}),
            data={"subject": "Test Topic"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertIsNotNone(Topic.objects.get(subject="Test Topic"))

    def test_topic_create_blank(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        response = self.client.post(
            reverse("boards:topic-create", kwargs={"slug": board.slug}),
            data={"subject": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "subject", "This field is required.")

    def test_topic_create_invalid(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        response = self.client.post(
            reverse("boards:topic-create", kwargs={"slug": board.slug}),
            data={"subject": "x" * 401},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response, "form", "subject", "Ensure this value has at most 400 characters (it has 401)."
        )

    async def test_topic_created_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board = await sync_to_async(Board.objects.get)(title="Test Board")
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username="testuser1", password="1X<ISRUkw+tuK")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.topic_created_url, data={"subject": "Test Topic"})
        topic = await sync_to_async(Topic.objects.get)(subject="Test Topic")
        message = await communicator.receive_from()
        self.assertIn("topic_created", message)
        self.assertIn(f'"topic_pk": {topic.id}', message)


class TopicUpdateViewTest(TestCase):
    topic_updated_url = ""

    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)
        cls.topic_updated_url = reverse("boards:topic-update", kwargs={"slug": board.slug, "pk": topic.pk})

    def test_anonymous_permissions(self):
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)

    def test_staff_permissions(self):
        User.objects.create_user(username="staff", password="83jKJ+!fdjP", is_staff=True)
        self.client.login(username="staff", password="83jKJ+!fdjP")
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)

    def test_topic_update_success(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.post(
            reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}),
            data={"subject": "Test Topic NEW"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertIsNotNone(Topic.objects.get(subject="Test Topic NEW"))

    def test_topic_update_blank(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.post(
            reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}),
            data={"subject": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "subject", "This field is required.")

    def test_topic_update_invalid(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.post(
            reverse("boards:topic-update", kwargs={"slug": topic.board.slug, "pk": topic.id}),
            data={"subject": "x" * 401},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response, "form", "subject", "Ensure this value has at most 400 characters (it has 401)."
        )

    async def test_topic_updated_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board = await sync_to_async(Board.objects.get)(title="Test Board")
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username="testuser1", password="1X<ISRUkw+tuK")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        topic = await sync_to_async(Topic.objects.get)(subject="Test Topic")
        await sync_to_async(self.client.post)(self.topic_updated_url, data={"subject": "Test Topic NEW"})
        message = await communicator.receive_from()
        self.assertIn("topic_updated", message)
        self.assertIn(f'"topic_pk": {topic.id}', message)


class TopicDeleteViewTest(TestCase):
    topic_deleted_url = ""

    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)
        cls.topic_deleted_url = reverse("boards:topic-delete", kwargs={"slug": board.slug, "pk": topic.id})

    def test_anonymous_permissions(self):
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(reverse("boards:topic-delete", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(reverse("boards:topic-delete", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(reverse("boards:topic-delete", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:topic-delete", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertRaises(Topic.DoesNotExist, Topic.objects.get, id=topic.id)
        self.assertEqual(response.status_code, 204)

    def test_staff_permissions(self):
        User.objects.create_user(username="staff", password="83jKJ+!fdjP", is_staff=True)
        self.client.login(username="staff", password="83jKJ+!fdjP")
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(reverse("boards:topic-delete", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:topic-delete", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertRaises(Topic.DoesNotExist, Topic.objects.get, id=topic.id)
        self.assertEqual(response.status_code, 204)

    async def test_topic_deleted_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board = await sync_to_async(Board.objects.get)(title="Test Board")
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username="testuser1", password="1X<ISRUkw+tuK")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        topic = await sync_to_async(Topic.objects.get)(subject="Test Topic")
        await sync_to_async(self.client.post)(self.topic_deleted_url)
        message = await communicator.receive_from()
        self.assertIn("topic_deleted", message)
        self.assertIn(f'"topic_pk": {topic.id}', message)


class DeleteTopicPostsViewTest(TestCase):
    topic_posts_delete_url = ""

    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)
        cls.topic_posts_delete_url = reverse(
            "boards:topic-posts-delete", kwargs={"slug": board.slug, "topic_pk": topic.id}
        )
        for i in range(10):
            Post.objects.create(topic=topic, content=f"Test Post {i}", user=test_user1)

    def test_anonymous_permissions(self):
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(
            reverse("boards:topic-posts-delete", kwargs={"slug": topic.board.slug, "topic_pk": topic.id})
        )
        self.assertEqual(response.status_code, 302)

    def test_owner_permissions(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(
            reverse("boards:topic-posts-delete", kwargs={"slug": topic.board.slug, "topic_pk": topic.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.filter(topic=topic).count(), 10)

        response = self.client.post(
            reverse("boards:topic-posts-delete", kwargs={"slug": topic.board.slug, "topic_pk": topic.id})
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.filter(topic=topic).count(), 0)

    async def test_topic_posts_deleted_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board = await sync_to_async(Board.objects.get)(title="Test Board")
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username="testuser1", password="1X<ISRUkw+tuK")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.topic_posts_delete_url)
        for _ in range(10):
            message = await communicator.receive_from()
            self.assertIn("post_deleted", message)


class PostCreateViewTest(TestCase):
    post_create_url = ""

    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        test_user3 = User.objects.create_user(username="testuser3", password="3y6d0A8sB?5")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        board.preferences.moderators.add(test_user3)
        board.preferences.save()
        topic = Topic.objects.create(subject="Test Topic", board=board)
        cls.post_create_url = reverse("boards:post-create", kwargs={"slug": board.slug, "topic_pk": topic.id})

    def test_anonymous_permissions(self):
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(
            reverse("boards:post-create", kwargs={"slug": topic.board.slug, "topic_pk": topic.id})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": topic.board.slug, "topic_pk": topic.id}),
            data={"content": "Test Message anon"},
        )
        topic = Topic.objects.prefetch_related("posts").get(subject="Test Topic")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(topic.posts.first().content, "Test Message anon")

    def test_post_session_key(self):
        topic = Topic.objects.get(subject="Test Topic")
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": topic.board.slug, "topic_pk": topic.id}),
            data={"content": "Test Post"},
        )
        post = Post.objects.get(content="Test Post")
        self.assertEqual(self.client.session.session_key, post.session_key)

    def test_post_approval(self):
        board = Board.objects.get(title="Test Board")
        board.preferences.require_approval = True
        board.preferences.save()
        topic = Topic.objects.get(subject="Test Topic")
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": board.slug, "topic_pk": topic.pk}),
            data={"content": "Test Post"},
        )
        post = Post.objects.get(content="Test Post")
        self.assertEqual(post.approved, False)

        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": board.slug, "topic_pk": topic.pk}),
            data={"content": "Test Post user1"},
        )
        post = Post.objects.get(content="Test Post user1")
        self.assertEqual(post.approved, True)  # Board owner can post without approval

        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": board.slug, "topic_pk": topic.pk}),
            data={"content": "Test Post user2"},
        )
        post = Post.objects.get(content="Test Post user2")
        self.assertEqual(post.approved, False)  # Normal user needs approval

        self.client.login(username="testuser3", password="3y6d0A8sB?5")
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": board.slug, "topic_pk": topic.pk}),
            data={"content": "Test Post user3"},
        )
        post = Post.objects.get(content="Test Post user3")
        self.assertEqual(post.approved, True)  # Moderator can post without approval

    async def test_post_created_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board = await sync_to_async(Board.objects.get)(title="Test Board")
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username="testuser1", password="1X<ISRUkw+tuK")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.post_create_url, data={"content": "Test Post"})
        post = await sync_to_async(Post.objects.get)(content="Test Post")
        self.assertIsNotNone(post)
        topic = await sync_to_async(Topic.objects.get)(subject="Test Topic")
        message = await communicator.receive_from()
        self.assertIn("post_created", message)
        self.assertIn(f'"topic_pk": {topic.id}', message)


class PostUpdateViewTest(TestCase):
    post_updated_url = ""

    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        test_user3 = User.objects.create_user(username="testuser3", password="3y6d0A8sB?5")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        board.preferences.moderators.add(test_user3)
        board.preferences.save()
        topic = Topic.objects.create(subject="Test Topic", board=board)
        post = Post.objects.create(
            content="Test Post",
            topic=topic,
        )
        cls.post_updated_url = reverse("boards:post-update", kwargs={"slug": board.slug, "pk": post.id})

    def test_anonymous_permissions(self):
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": "test-board", "topic_pk": topic.pk}),
            data={"content": "Test Post anon"},
        )
        post = Post.objects.get(content="Test Post anon")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.session.session_key, post.session_key)
        response = self.client.post(
            reverse("boards:post-update", kwargs={"slug": post.topic.board.slug, "pk": post.id}),
            data={"content": "Test Post anon NEW"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.get(id=post.id).content, "Test Post anon NEW")

    def test_other_user_permissions(self):
        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        post = Post.objects.get(content="Test Post")
        response = self.client.get(
            reverse("boards:post-update", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_board_moderator_permissions(self):
        self.client.login(username="testuser3", password="3y6d0A8sB?5")
        post = Post.objects.get(content="Test Post")
        response = self.client.get(
            reverse("boards:post-update", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("boards:post-update", kwargs={"slug": post.topic.board.slug, "pk": post.id}),
            data={"content": "Test Post NEW"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.get(id=post.id).content, "Test Post NEW")

    def test_owner_permissions(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        post = Post.objects.get(content="Test Post")
        response = self.client.get(
            reverse("boards:post-update", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("boards:post-update", kwargs={"slug": post.topic.board.slug, "pk": post.id}),
            data={"content": "Test Post NEW"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.get(id=post.id).content, "Test Post NEW")

    async def test_post_updated_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board = await sync_to_async(Board.objects.get)(title="Test Board")
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username="testuser1", password="1X<ISRUkw+tuK")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        post = await sync_to_async(Post.objects.get)(content="Test Post")
        await sync_to_async(self.client.post)(self.post_updated_url, data={"content": "Test Post NEW"})
        message = await communicator.receive_from()
        self.assertIn("post_updated", message)
        self.assertIn(f'"post_pk": {post.id}', message)


class PostDeleteViewTest(TestCase):
    post_deleted_url = ""

    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        test_user3 = User.objects.create_user(username="testuser3", password="3y6d0A8sB?5")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        board.preferences.moderators.add(test_user3)
        board.preferences.save()
        topic = Topic.objects.create(subject="Test Topic", board=board)
        post = Post.objects.create(content="Test Post", topic=topic)
        cls.post_deleted_url = reverse("boards:post-delete", kwargs={"slug": board.slug, "pk": post.id})

    def test_anonymous_permissions(self):
        post = Post.objects.get(content="Test Post")
        self.client.post(reverse("boards:post-delete", kwargs={"slug": "test-board", "pk": post.pk}))
        self.assertEqual(Post.objects.count(), 1)
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": "test-board", "topic_pk": post.topic.pk}),
            data={"content": "Test Post anon"},
        )
        post2 = Post.objects.get(content="Test Post anon")
        self.assertEqual(Post.objects.count(), 2)
        self.client.post(reverse("boards:post-delete", kwargs={"slug": "test-board", "pk": post2.pk}))
        self.assertEqual(Post.objects.count(), 1)

    def test_other_user_permissions(self):
        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        post = Post.objects.get(content="Test Post")
        response = self.client.post(
            reverse("boards:post-delete", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Post.objects.count(), 1)

    def test_board_moderator_permissions(self):
        self.client.login(username="testuser3", password="3y6d0A8sB?5")
        post = Post.objects.get(content="Test Post")
        response = self.client.post(
            reverse("boards:post-delete", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.count(), 0)

    def test_owner_permissions(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        post = Post.objects.get(content="Test Post")
        response = self.client.post(
            reverse("boards:post-delete", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.count(), 0)

    async def test_post_deleted_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board = await sync_to_async(Board.objects.get)(title="Test Board")
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username="testuser1", password="1X<ISRUkw+tuK")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        post = await sync_to_async(Post.objects.get)(content="Test Post")
        await sync_to_async(self.client.post)(self.post_deleted_url)
        message = await communicator.receive_from()
        self.assertIn("post_deleted", message)
        self.assertIn(f'"post_pk": {post.id}', message)


class ReactionsDeleteViewTest(TestCase):
    reactions_delete_url = ""

    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        test_user3 = User.objects.create_user(username="testuser3", password="3y6d0A8sB?5")
        board = Board.objects.create(
            title="Test Board", slug="000000", description="Test Description", owner=test_user1
        )
        board.preferences.moderators.add(test_user3)
        board.preferences.reaction_type = "l"
        board.preferences.save()
        topic = Topic.objects.create(subject="Test Topic", board=board)
        for i in range(5):
            post = Post.objects.create(content=f"Test Post {i}", topic=topic)
            for type in REACTION_TYPE[1:]:
                for j in range(5):
                    Reaction.objects.create(post=post, session_key=f"{i}{j}", type=type[0], reaction_score="1")
        cls.reactions_delete_url = reverse(
            "boards:post-reactions-delete", kwargs={"slug": board.slug, "pk": Post.objects.first().pk}
        )

    def test_anonymous_permissions(self):
        post = Post.objects.get(content="Test Post 0")
        response = self.client.get(reverse("boards:post-reactions-delete", kwargs={"slug": "000000", "pk": post.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

        response = self.client.post(reverse("boards:post-reactions-delete", kwargs={"slug": "000000", "pk": post.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

    def test_moderator_permissions(self):
        self.client.login(username="testuser3", password="3y6d0A8sB?5")
        post = Post.objects.get(content="Test Post 0")
        response = self.client.get(reverse("boards:post-reactions-delete", kwargs={"slug": "000000", "pk": post.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

        response = self.client.post(reverse("boards:post-reactions-delete", kwargs={"slug": "000000", "pk": post.pk}))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1) - 5)

    async def test_post_toggle_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board = await sync_to_async(Board.objects.get)(title="Test Board")
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username="testuser1", password="1X<ISRUkw+tuK")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        post = await sync_to_async(Post.objects.first)()
        await sync_to_async(self.client.post)(self.reactions_delete_url)
        message = await communicator.receive_from()
        self.assertIn("reaction_updated", message)
        self.assertIn(f'"post_pk": {post.pk}', message)


class BoardListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_superuser(username="testuser2", password="2HJ1vRV0Z&3iD")
        for i in range(3):
            Board.objects.create(
                title=f"Test Board {i} - {test_user1.username}", description="Test Description", owner=test_user1
            )
            Board.objects.create(
                title=f"Test Board {i} - {test_user2.username}", description="Test Description", owner=test_user2
            )

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:board-list"))
        self.assertEqual(response.status_code, 302)

    def test_user_index(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("boards:board-list"), {}, HTTP_REFERER=reverse("boards:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "boards/components/board_list.html")
        self.assertEqual(len(response.context["boards"]), 3)

    def test_user_no_perm_all_boards(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("boards:board-list"), {}, HTTP_REFERER=reverse("boards:index-all"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "boards/components/board_list.html")
        self.assertEqual(len(response.context["boards"]), 3)

    def test_user_perm_all_boards(self):
        test_user1 = User.objects.get(username="testuser1")
        test_user1.user_permissions.add(Permission.objects.get(codename="can_view_all_boards"))
        test_user1.save()
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("boards:board-list"), {}, HTTP_REFERER=reverse("boards:index-all"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "boards/components/board_list.html")
        self.assertEqual(len(response.context["boards"]), 5)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertEqual(len(response.context["page_obj"].paginator.page_range), 2)

    def test_user_perm_second_page(self):
        test_user1 = User.objects.get(username="testuser1")
        test_user1.user_permissions.add(Permission.objects.get(codename="can_view_all_boards"))
        test_user1.save()
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(
            reverse("boards:board-list"), {"page": 2}, HTTP_REFERER=reverse("boards:index-all")
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "boards/components/board_list.html")
        self.assertEqual(len(response.context["boards"]), 1)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["page_obj"].paginator.page_range), 2)


class TopicFetchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        Topic.objects.create(subject="Test Topic", board=board)

    def test_topic_fetch(self):
        topic = Topic.objects.get(subject="Test Topic")
        response = self.client.get(reverse("boards:topic-fetch", kwargs={"slug": topic.board.slug, "pk": topic.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["topic"], topic)


class PostFetchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        test_user3 = User.objects.create_user(username="testuser3", password="3y6d0A8sB?5")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        board.preferences.moderators.add(test_user3)
        board.preferences.save()
        topic = Topic.objects.create(subject="Test Topic", board=board)
        Post.objects.create(content="Test Post", topic=topic, session_key="testing_key", approved=False)

    def test_post_fetch(self):
        post = Post.objects.get(content="Test Post")
        post.approved = True
        post.save()
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["post"], post)
        self.assertContains(response, "Test Post", html=True)

    def test_post_fetch_content_anonymous_not_approved(self):
        board = Board.objects.get(title="Test Board")
        board.preferences.require_approval = True
        board.preferences.save()
        self.client.get(reverse("boards:board", kwargs={"slug": board.slug}))
        post = Post.objects.get(content="Test Post")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertNotContains(response, "Test Post", html=True)

    def test_post_fetch_content_other_user_not_approved(self):
        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(title="Test Board")
        board.preferences.require_approval = True
        board.preferences.save()
        self.client.get(reverse("boards:board", kwargs={"slug": board.slug}))
        post = Post.objects.get(content="Test Post")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertNotContains(response, "Test Post", html=True)

    def test_post_fetch_content_board_moderator_not_approved(self):
        self.client.login(username="testuser3", password="3y6d0A8sB?5")
        post = Post.objects.get(content="Test Post")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertContains(response, "Test Post", html=True)

    def test_post_fetch_content_owner_not_approved(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        post = Post.objects.get(content="Test Post")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertContains(response, "Test Post", html=True)

    def test_post_fetch_content_can_approve_not_approved(self):
        test_user4 = User.objects.create_user(username="testuser4", password="2HJ1vRV0Z&3iD")
        test_user4.user_permissions.add(Permission.objects.get(codename="can_approve_posts"))
        self.client.login(username="testuser4", password="2HJ1vRV0Z&3iD")
        post = Post.objects.get(content="Test Post")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertContains(response, "Test Post", html=True)


class PostFooterFetchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        test_user3 = User.objects.create_user(username="testuser3", password="3y6d0A8sB?5")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        board.preferences.moderators.add(test_user3)
        board.preferences.reaction_type = "l"
        board.preferences.save()
        topic = Topic.objects.create(subject="Test Topic", board=board)
        post = Post.objects.create(content="Test Post", topic=topic, session_key="testing_key", approved=False)
        for type in REACTION_TYPE[1:]:
            Reaction.objects.create(post=post, type=type[0], user=test_user1)

    def test_post_footer_fetch_anonymous(self):
        post = Post.objects.get(content="Test Post")
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

            response = self.client.get(
                reverse("boards:post-footer-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.pk})
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["post"], post)
            self.assertNotContains(response, icon)

            post.approved = True
            post.save()
            response = self.client.get(
                reverse("boards:post-footer-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.pk})
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["post"], post)
            self.assertContains(response, icon)

    def test_post_footer_fetch_moderator(self):
        self.client.login(username="testuser3", password="3y6d0A8sB?5")
        post = Post.objects.get(content="Test Post")
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

            response = self.client.get(
                reverse("boards:post-footer-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.pk})
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["post"], post)
            self.assertContains(response, icon)

            post.approved = True
            post.save()
            response = self.client.get(
                reverse("boards:post-footer-fetch", kwargs={"slug": post.topic.board.slug, "pk": post.pk})
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["post"], post)
            self.assertContains(response, icon)


class PostToggleApprovalViewTest(TestCase):
    post_approval_url = ""

    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        test_user3 = User.objects.create_user(username="testuser3", password="3y6d0A8sB?5")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        board.preferences.moderators.add(test_user3)
        board.preferences.require_approval = True
        board.preferences.save()
        topic = Topic.objects.create(subject="Test Topic", board=board)
        post = Post.objects.create(content="Test Post", topic=topic, session_key="testing_key", approved=False)
        cls.post_approval_url = reverse("boards:post-toggle-approval", kwargs={"slug": board.slug, "pk": post.id})

    def test_post_toggle_approval_anonymous(self):
        post = Post.objects.get(content="Test Post")
        self.assertFalse(post.approved)
        response = self.client.post(
            reverse("boards:post-toggle-approval", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 302)

    def test_post_toggle_approval_other_user(self):
        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        post = Post.objects.get(content="Test Post")
        self.assertFalse(post.approved)
        response = self.client.post(
            reverse("boards:post-toggle-approval", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_post_toggle_approval_board_moderator(self):
        self.client.login(username="testuser3", password="3y6d0A8sB?5")
        post = Post.objects.get(content="Test Post")
        self.assertFalse(post.approved)
        response = self.client.post(
            reverse("boards:post-toggle-approval", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Post.objects.get(content="Test Post").approved)
        response = self.client.post(
            reverse("boards:post-toggle-approval", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Post.objects.get(content="Test Post").approved)

    def test_post_toggle_approval_owner(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        post = Post.objects.get(content="Test Post")
        self.assertFalse(post.approved)
        response = self.client.post(
            reverse("boards:post-toggle-approval", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Post.objects.get(content="Test Post").approved)
        response = self.client.post(
            reverse("boards:post-toggle-approval", kwargs={"slug": post.topic.board.slug, "pk": post.id})
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Post.objects.get(content="Test Post").approved)

    async def test_post_toggle_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board = await sync_to_async(Board.objects.get)(title="Test Board")
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username="testuser1", password="1X<ISRUkw+tuK")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        post = await sync_to_async(Post.objects.get)(content="Test Post")
        await sync_to_async(self.client.post)(self.post_approval_url)
        message = await communicator.receive_from()
        self.assertIn("post_updated", message)
        self.assertIn(f'"post_pk": {post.id}', message)
        await sync_to_async(self.client.post)(self.post_approval_url)
        message = await communicator.receive_from()
        self.assertIn("post_updated", message)
        self.assertIn(f'"post_pk": {post.pk}', message)


class PostReactionViewTest(TestCase):
    post_reaction_url = ""

    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        topic = Topic.objects.create(subject="Test Topic", board=board)
        post = Post.objects.create(content="Test Post", topic=topic, session_key="testing_key", user=test_user1)
        cls.post_reaction_url = reverse("boards:post-reaction", kwargs={"slug": board.slug, "pk": post.pk})

    def test_post_reaction_repeat_anonymous(self):
        post = Post.objects.get(content="Test Post")
        self.assertEqual(Reaction.objects.count(), 0)

        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            post.topic.board.preferences.reaction_type = type
            post.topic.board.preferences.save()

            response = self.client.post(
                reverse("boards:post-reaction", kwargs={"slug": post.topic.board.slug, "pk": post.pk}),
                {"score": 1},
            )
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 1)

            response = self.client.post(
                reverse("boards:post-reaction", kwargs={"slug": post.topic.board.slug, "pk": post.pk}),
                {"score": 1},
            )
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 0)

    def test_post_reaction_score_changed(self):
        post = Post.objects.get(content="Test Post")
        self.assertEqual(Reaction.objects.count(), 0)

        for _type in REACTION_TYPE[2:]:  # like only has one score
            type = _type[0]
            post.topic.board.preferences.reaction_type = type
            post.topic.board.preferences.save()
            if type == "v":
                second_score = -1
            elif type == "s":
                second_score = 2

            response = self.client.post(
                reverse("boards:post-reaction", kwargs={"slug": post.topic.board.slug, "pk": post.pk}),
                {"score": 1},
            )
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 1)
            self.assertEqual(Reaction.objects.first().reaction_score, 1)

            response = self.client.post(
                reverse("boards:post-reaction", kwargs={"slug": post.topic.board.slug, "pk": post.pk}),
                {"score": second_score},
            )
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 1)
            self.assertEqual(Reaction.objects.first().reaction_score, second_score)

            post.reactions.all().delete()

    def test_post_reaction_disabled(self):
        post = Post.objects.get(content="Test Post")
        self.assertEqual(Reaction.objects.count(), 0)

        response = self.client.post(
            reverse("boards:post-reaction", kwargs={"slug": post.topic.board.slug, "pk": post.pk}),
            {"score": 1},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Reaction.objects.count(), 0)

    def test_post_reaction_own_post(self):
        post = Post.objects.get(content="Test Post")
        self.assertEqual(Reaction.objects.count(), 0)

        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")

        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            post.topic.board.preferences.reaction_type = type
            post.topic.board.preferences.save()

            response = self.client.post(
                reverse("boards:post-reaction", kwargs={"slug": post.topic.board.slug, "pk": post.pk}),
                {"score": 1},
            )
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 0)

    async def test_reaction_updated_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board = await sync_to_async(Board.objects.get)(title="Test Board")
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        post = await sync_to_async(Post.objects.get)(content="Test Post")
        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            preferences = await sync_to_async(BoardPreferences.objects.get)(board=board)
            preferences.reaction_type = type
            await sync_to_async(preferences.save)()
            message = await communicator.receive_from()
            self.assertIn("board_preferences_changed", message)
            await sync_to_async(self.client.post)(self.post_reaction_url, data={"score": 1})
            message = await communicator.receive_from()
            self.assertIn("reaction_updated", message)
            self.assertIn(f'"post_pk": {post.id}', message)


MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ImageSelectViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        module_dir = os.path.dirname(__file__)
        image_path = os.path.join(module_dir, "images/white_horizontal.png")
        for type, text in IMAGE_TYPE:
            for i in range(5):
                with open(image_path, "rb") as image_file:
                    image = Image(
                        type=type,
                        image=SimpleUploadedFile(
                            name=f"{type}-{i}.png",
                            content=image_file.read(),
                            content_type="image/png",
                        ),
                        title=f"{text} {i}",
                    )
                    image.save()

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
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        for type, _ in IMAGE_TYPE:
            response = self.client.get(reverse("boards:image-select", kwargs={"type": type}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["images"].count(), Image.objects.filter(type=type).count())


class QrViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        test_user3 = User.objects.create_user(username="testuser3", password="3y6d0A8sB?5")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)
        board.preferences.moderators.add(test_user3)
        board.preferences.save()

    def test_qr_anonymous(self):
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/accounts/login/?next=/boards/{board.slug}/qr/")

    def test_qr_other_user(self):
        self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_qr_board_moderator(self):
        self.client.login(username="testuser3", password="3y6d0A8sB?5")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("data:image/png;base64", response.content.decode("utf-8"))

    def test_qr_owner(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("data:image/png;base64", response.content.decode("utf-8"))

    def test_qr_staff(self):
        User.objects.create_user(username="testuser4", password="2HJ1vRV0Z&3iD", is_staff=True)
        self.client.login(username="testuser4", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(title="Test Board")
        response = self.client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
