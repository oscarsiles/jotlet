import shutil

import pytest
from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.templatetags.static import static
from django.urls import reverse
from pytest_django.asserts import assertFormError

from boards.models import IMAGE_TYPE, Board, BoardPreferences, Image
from boards.routing import websocket_urlpatterns
from boards.views.board import BoardView
from jotlet.tests.utils import create_htmx_session


class TestBoardView:
    def test_anonymous_permissions(self, client, board):
        response = client.get(reverse("boards:board", kwargs={"slug": board.slug}))
        assert response.status_code == 200

    def test_board_not_exist(self, client, board):
        board.slug = "000001"
        board.save()
        response = client.get(reverse("boards:board", kwargs={"slug": "000000"}))
        assert response.status_code == 404

    def test_link_headers(self, client, board):
        url = reverse("boards:board", kwargs={"slug": board.slug})
        response = client.get(url)
        link_header = response.get("Link")
        assert link_header is not None
        assert f"<{static('css/vendor/bootstrap-5.3.0-alpha3.min.css')}>; rel=preload; as=style" in link_header
        assert f"<{static('css/vendor/easymde-2.18.0.min.css')}>; rel=preload; as=style" in link_header

        assert f"<{static('js/vendor/jdenticon-3.2.0.min.js')}>; rel=preload; as=script" in link_header
        assert "boards/js/components/board_mathjax.js" not in link_header
        board.preferences.enable_latex = True
        board.preferences.enable_chemdoodle = True
        board.preferences.enable_identicons = False
        board.preferences.save()
        response = client.get(url)
        link_header = response.get("Link")
        assert f"<{static('boards/js/components/board_mathjax.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/chemdoodleweb-9.5.0/ChemDoodleWeb.js')}>; rel=preload; as=script" in link_header
        assert (
            f"<{static('js/vendor/chemdoodleweb-9.5.0/ChemDoodleWeb-uis.js')}>; rel=preload; as=script" in link_header
        )
        assert f"<{static('css/vendor/chemdoodleweb-9.5.0/ChemDoodleWeb.css')}>; rel=preload; as=style" in link_header
        assert (
            f"<{static('css/vendor/chemdoodleweb-9.5.0/jquery-ui-1.11.4.custom.css')}>; rel=preload; as=style"
            in link_header
        )
        assert "js/vendor/jdenticon-3.2.0.min.js" not in link_header

    @pytest.mark.parametrize(
        "current_url,response_template",
        [
            ("", "boards/board_index.html"),  # request with no current_url
            (reverse("boards:index"), "boards/board_index.html"),  # request from index
            (reverse("boards:index-all"), "boards/board_index.html"),  # request from index-all
            (
                reverse("boards:board", kwargs={"slug": "00000001"}),
                "boards/components/board.html",
            ),  # request from board URL
            (
                reverse("boards:board", kwargs={"slug": "00000000"}),
                "boards/board_index.html",
            ),  # request from another board
        ],
    )
    def test_htmx_requests(self, rf, board, user, current_url, response_template):
        board.slug = "00000001"
        board.save()
        kwargs = {"slug": board.slug}

        request = rf.get(
            reverse("boards:board", kwargs=kwargs),
            HTTP_HX_REQUEST="true",
            HTTP_HX_CURRENT_URL=current_url,
        )
        request.user = user
        create_htmx_session(request)

        response = BoardView.as_view()(request, **kwargs)
        assert response.status_code == 200
        assert response.template_name[0] == response_template

    def test_topic_ordering(self, client, board, topic_factory):
        topic1 = topic_factory(board=board)
        topic2 = topic_factory(board=board)
        topic3 = topic_factory(board=board)

        response = client.get(reverse("boards:board", kwargs={"slug": board.slug}))
        assert response.status_code == 200
        assert list(response.context["topics"]) == [topic1, topic2, topic3]


class TestBoardPreferencesView:
    def test_board_preferences_anonymous_permissions(self, client, board):
        response = client.get(reverse("boards:board-preferences", kwargs={"slug": board.slug}))
        assert response.status_code == 302
        assert response.url == f"/accounts/login/?next=/boards/{board.slug}/preferences/"

    def test_board_references_other_user_permissions(self, client, board, user2):
        client.force_login(user2)
        response = client.get(reverse("boards:board-preferences", kwargs={"slug": board.slug}))
        assert response.status_code == 403

    def test_board_preferences_owner_permissions(self, client, board, user):
        client.force_login(user)
        response = client.get(reverse("boards:board-preferences", kwargs={"slug": board.slug}))
        assert response.status_code == 200

    def test_board_preferences_nonexistent_preferences(self, client, board, user):
        client.force_login(user)
        preferences_pk = board.preferences.pk
        board.preferences.delete()
        pytest.raises(BoardPreferences.DoesNotExist, BoardPreferences.objects.get, pk=preferences_pk)
        response = client.get(reverse("boards:board-preferences", kwargs={"slug": board.slug}))
        assert response.status_code == 200
        preferences = BoardPreferences.objects.get(board=board)
        assert preferences.board == board

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_preferences_changed_websocket_message(self, client, board, user):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        response = await sync_to_async(client.post)(
            reverse("boards:board-preferences", kwargs={"slug": board.slug}),
            data={
                "board_type": "d",
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
        await communicator.disconnect()
        assert "board_preferences_changed" in message
        assert response.status_code == 204


class TestCreateBoardView:
    def test_anonymous_permissions(self, client):
        response = client.get(reverse("boards:board-create"))
        assert response.status_code == 302

    def test_user_permissions(self, client, user):
        client.force_login(user)
        response = client.get(reverse("boards:board-create"))
        assert str(response.context["user"]) == user.username
        assert response.status_code == 200

    def test_board_create_success(self, client, user):
        client.force_login(user)
        response = client.post(
            reverse("boards:board-create"),
            {
                "title": "Test Board",
                "description": "Test Board Description",
            },
        )
        assert response.status_code == 200
        board = Board.objects.get(title="Test Board")
        assert board.description == "Test Board Description"

    def test_board_create_blank_title(self, client, user):
        client.force_login(user)
        response = client.post(
            reverse("boards:board-create"),
            {
                "title": "",
                "description": "Test Board Description",
            },
        )
        assert response.status_code == 200
        assertFormError(response.context["form"], "title", "This field is required.")

    def test_board_create_blank_description(self, client, user):
        client.force_login(user)
        response = client.post(
            reverse("boards:board-create"),
            {
                "title": "Test Board",
                "description": "",
            },
        )
        assert response.status_code == 200
        board = Board.objects.get(title="Test Board")
        assert board.title == "Test Board"
        assert board.description == ""

    def test_board_create_invalid(self, client, user):
        client.force_login(user)
        response = client.post(
            reverse("boards:board-create"),
            {
                "title": "x" * 51,
                "description": "x" * 101,
            },
        )
        assert response.status_code == 200
        assertFormError(response.context["form"], "title", "Ensure this value has at most 50 characters (it has 51).")
        assertFormError(
            response.context["form"], "description", "Ensure this value has at most 100 characters (it has 101)."
        )


class TestUpdateBoardView:
    def test_anonymous_permissions(self, client, board):
        response = client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        assert response.status_code == 302

    def test_other_user_permissions(self, client, user2, board):
        client.force_login(user2)
        response = client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        assert response.status_code == 403

    def test_owner_permissions(self, client, board, user):
        client.force_login(user)
        response = client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        assert response.status_code == 200

    def test_staff_permissions(self, client, board, user_staff):
        client.force_login(user_staff)
        response = client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        assert response.status_code == 200

    def test_board_update_success(self, client, board, user):
        client.force_login(user)
        response = client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {
                "title": "Test Board NEW",
                "description": "Test Board Description NEW",
            },
        )
        assert response.status_code == 200
        board.refresh_from_db()
        assert board.title == "Test Board NEW"
        assert board.description == "Test Board Description NEW"

    def test_board_update_blank(self, client, board, user):
        client.force_login(user)
        response = client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {
                "title": "",
                "description": "",
            },
        )
        assert response.status_code == 200
        assertFormError(response.context["form"], "title", "This field is required.")

    def test_board_update_invalid(self, client, board, user):
        client.force_login(user)
        response = client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {"title": "x" * 51, "description": "x" * 101},
        )
        assert response.status_code == 200
        assertFormError(
            response.context["form"],
            "title",
            "Ensure this value has at most 50 characters (it has 51).",
        )
        assertFormError(
            response.context["form"],
            "description",
            "Ensure this value has at most 100 characters (it has 101).",
        )


class TestDeleteBoardView:
    def test_anonymous_permissions(self, client, board):
        response = client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        assert response.status_code == 302

    def test_other_user_permissions(self, client, board, user2):
        client.force_login(user2)
        response = client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        assert response.status_code == 403

    def test_owner_permissions(self, client, board, user):
        client.force_login(user)
        response = client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        assert response.status_code == 200
        response = client.post(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        assert response.status_code == 302
        assert len(Board.objects.all()) == 0

    def test_staff_permissions(self, client, board, user_staff):
        client.force_login(user_staff)
        response = client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        assert response.status_code == 200
        response = client.post(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        assert response.status_code == 302
        assert len(Board.objects.all()) == 0

    def test_delete_board_with_reactions(self, client, board, user, topic_factory, post_factory, reaction_factory):
        client.force_login(user)
        topic = topic_factory(board=board)
        post = post_factory(topic=topic)
        reaction_factory(post=post)
        response = client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        assert response.status_code == 200
        response = client.post(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        assert response.status_code == 302
        assert len(Board.objects.all()) == 0


class TestImageSelectView:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, board, image_factory):
        for image_type, _ in IMAGE_TYPE:
            image_factory.create_batch(5, board=board if image_type == "p" else None, image_type=image_type)

    @classmethod
    def teardown_class(cls):
        from django.conf import settings

        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_image_select_anonymous(self, client):
        for image_type, _ in IMAGE_TYPE:
            response = client.get(reverse("boards:image-select", kwargs={"image_type": image_type}))
            assert response.status_code == 302
            assert response.url == f"/accounts/login/?next=/boards/image_select/{image_type}/"

    def test_image_select_logged_in(self, client, user):
        client.force_login(user)
        for image_type, _ in IMAGE_TYPE:
            response = client.get(reverse("boards:image-select", kwargs={"image_type": image_type}))
            assert response.status_code == 200
            assert response.context["images"].count() == Image.objects.filter(image_type=image_type).count()


class TestQrView:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, board, user3):
        board.preferences.moderators.add(user3)
        board.preferences.save()

    def test_qr_anonymous(self, client, board):
        response = client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        assert response.status_code == 302
        assert response.url == f"/accounts/login/?next=/boards/{board.slug}/qr/"

    def test_qr_other_user(self, client, board, user2):
        client.force_login(user2)
        response = client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        assert response.status_code == 403

    def test_qr_board_moderator(self, client, board, user3):
        client.force_login(user3)
        response = client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        assert response.status_code == 200
        assert "/qr_code/images/serve-qr-code-image/" in response.content.decode("utf-8")

    def test_qr_owner(self, client, board, user):
        client.force_login(user)
        response = client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        assert response.status_code == 200
        assert "/qr_code/images/serve-qr-code-image/" in response.content.decode("utf-8")

    def test_qr_staff(self, client, board, user_staff):
        client.force_login(user_staff)
        response = client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        assert response.status_code == 200
        assert "/qr_code/images/serve-qr-code-image/" in response.content.decode("utf-8")
