import shutil
import tempfile

from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse

from accounts.tests.factories import USER_TEST_PASSWORD, UserFactory
from boards.models import IMAGE_TYPE, Board, BoardPreferences, Image
from boards.routing import websocket_urlpatterns
from boards.tests.factories import BoardFactory, ImageFactory, PostFactory, ReactionFactory, TopicFactory
from boards.tests.utils import create_htmx_session
from boards.views.board import BoardView

MEDIA_ROOT = tempfile.mkdtemp()


class BoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.board = BoardFactory(owner=cls.user, slug="000001")

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:board", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_board_not_exist(self):
        response = self.client.get(reverse("boards:board", kwargs={"slug": "000000"}))
        self.assertEqual(response.status_code, 404)

    def test_link_headers(self):
        url = reverse("boards:board", kwargs={"slug": self.board.slug})
        response = self.client.get(url)
        link_header = response.get("Link")
        self.assertIsNotNone(link_header)
        self.assertIn(f"<{static('css/3rdparty/bootstrap-5.2.2.min.css')}>; rel=preload; as=style", link_header)
        self.assertIn(f"<{static('css/3rdparty/easymde-2.18.0.min.css')}>; rel=preload; as=style", link_header)

        self.assertIn(f"<{static('js/3rdparty/jdenticon-3.2.0.min.js')}>; rel=preload; as=script", link_header)
        self.assertNotIn("boards/js/components/board_mathjax.js", link_header)
        self.board.preferences.enable_latex = True
        self.board.preferences.enable_identicons = False
        self.board.preferences.save()
        response = self.client.get(url)
        link_header = response.get("Link")
        self.assertIn(f"<{static('boards/js/components/board_mathjax.js')}>; rel=preload; as=script", link_header)
        self.assertNotIn("js/3rdparty/jdenticon-3.2.0.min.js", link_header)

    def test_htmx_requests(self):
        kwargs = {"slug": self.board.slug}

        # request with no current_url
        request = self.factory.get(reverse("boards:board", kwargs=kwargs), HTTP_HX_REQUEST="true")
        request.user = self.user
        create_htmx_session(request)

        response = BoardView.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "boards/board_index.html")

        # request from index
        request = self.factory.get(
            reverse("boards:board", kwargs=kwargs),
            HTTP_HX_REQUEST="true",
            HTTP_HX_CURRENT_URL=reverse("boards:index"),
        )
        request.user = self.user
        create_htmx_session(request)

        response = BoardView.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "boards/board_index.html")

        # request from index-all
        request = self.factory.get(
            reverse("boards:board", kwargs=kwargs),
            HTTP_HX_REQUEST="true",
            HTTP_HX_CURRENT_URL=reverse("boards:index-all"),
        )
        request.user = self.user
        create_htmx_session(request)

        response = BoardView.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "boards/board_index.html")

        # request from board URL
        request = self.factory.get(
            reverse("boards:board", kwargs=kwargs),
            HTTP_HX_REQUEST="true",
            HTTP_HX_CURRENT_URL=reverse("boards:board", kwargs=kwargs),
        )
        request.user = self.user
        create_htmx_session(request)

        response = BoardView.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "boards/components/board.html")

        # request from another board URL
        request = self.factory.get(
            reverse("boards:board", kwargs=kwargs),
            HTTP_HX_REQUEST="true",
            HTTP_HX_CURRENT_URL=reverse("boards:board", kwargs={"slug": "000000"}),
        )
        request.user = self.user
        create_htmx_session(request)

        response = BoardView.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "boards/board_index.html")

    def test_topic_ordering(self):
        topic1 = TopicFactory(board=self.board)
        topic2 = TopicFactory(board=self.board)
        topic3 = TopicFactory(board=self.board)

        response = self.client.get(reverse("boards:board", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["topics"]), [topic1, topic2, topic3])


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
        self.assertIn("/qr_code/images/serve-qr-code-image/", response.content.decode("utf-8"))
