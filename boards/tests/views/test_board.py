from http import HTTPStatus

import pytest
from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.urls import reverse
from pytest_django.asserts import assertFormError
from pytest_lazy_fixtures import lf

from boards.models import IMAGE_TYPE, Board, BoardPreferences, Image, Reaction
from boards.routing import websocket_urlpatterns
from boards.views.board import BoardView
from jotlet.tests.utils import create_htmx_session


class TestBoardView:
    def test_anonymous_permissions(self, client, board):
        response = client.get(reverse("boards:board", kwargs={"slug": board.slug}))
        assert response.status_code == HTTPStatus.OK

    def test_board_not_exist(self, client, board):
        board.slug = "000001"
        board.save()
        response = client.get(reverse("boards:board", kwargs={"slug": "000000"}))
        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.parametrize(
        ("current_url", "response_template"),
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
        assert response.status_code == HTTPStatus.OK
        assert response.template_name[0] == response_template

    def test_topic_ordering(self, client, board, topic_factory):
        topic1 = topic_factory(board=board)
        topic2 = topic_factory(board=board)
        topic3 = topic_factory(board=board)

        response = client.get(reverse("boards:board", kwargs={"slug": board.slug}))
        assert response.status_code == HTTPStatus.OK
        assert list(response.context["topics"]) == [topic1, topic2, topic3]


class TestBoardPreferencesView:
    @pytest.fixture()
    def get_board_preferences_url(self, board):
        return reverse("boards:board-preferences", kwargs={"slug": board.slug})

    @pytest.mark.parametrize(
        ("test_user", "expected_status"),
        [
            (None, HTTPStatus.FOUND),
            (lf("user2"), HTTPStatus.FORBIDDEN),
            (lf("user"), HTTPStatus.OK),
        ],
    )
    def test_board_preferences_permissions(self, client, test_user, expected_status, get_board_preferences_url):
        if test_user:
            client.force_login(test_user)
        response = client.get(get_board_preferences_url)
        assert response.status_code == expected_status

    def test_board_preferences_nonexistent_preferences(self, client, board, user, get_board_preferences_url):
        client.force_login(user)
        preferences_pk = board.preferences.pk
        board.preferences.delete()
        pytest.raises(BoardPreferences.DoesNotExist, BoardPreferences.objects.get, pk=preferences_pk)
        response = client.get(get_board_preferences_url)
        assert response.status_code == HTTPStatus.OK
        preferences = BoardPreferences.objects.get(board=board)
        assert preferences.board == board

    @pytest.mark.asyncio()
    @pytest.mark.django_db(transaction=True)
    async def test_preferences_changed_websocket_message(self, client, board, user, get_board_preferences_url):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        response = await sync_to_async(client.post)(
            get_board_preferences_url,
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
        assert response.status_code == HTTPStatus.NO_CONTENT


class TestCreateBoardView:
    def test_anonymous_permissions(self, client):
        response = client.get(reverse("boards:board-create"))
        assert response.status_code == HTTPStatus.FOUND

    def test_user_permissions(self, client, user):
        client.force_login(user)
        response = client.get(reverse("boards:board-create"))
        assert str(response.context["user"]) == user.username
        assert response.status_code == HTTPStatus.OK

    def test_board_create_success(self, client, user):
        self._post_board_create(client, user, "Test Board", "Test Board Description")
        board = Board.objects.get(title="Test Board")
        assert board.description == "Test Board Description"

    def test_board_create_blank_title(self, client, user):
        response = self._post_board_create(client, user, "", "Test Board Description")
        assertFormError(response.context["form"], "title", "This field is required.")

    def test_board_create_blank_description(self, client, user):
        self._post_board_create(client, user, "Test Board", "")
        board = Board.objects.get(title="Test Board")
        assert board.title == "Test Board"
        assert board.description == ""

    def _post_board_create(self, client, user, title, description):
        client.force_login(user)
        response = client.post(reverse("boards:board-create"), {"title": title, "description": description})
        assert response.status_code == HTTPStatus.OK
        return response

    def test_board_create_invalid(self, client, user):
        client.force_login(user)
        response = self._post_board_create(client, user, "x" * 51, "x" * 101)
        assertFormError(response.context["form"], "title", "Ensure this value has at most 50 characters (it has 51).")
        assertFormError(
            response.context["form"], "description", "Ensure this value has at most 100 characters (it has 101)."
        )


class TestUpdateBoardView:
    def test_anonymous_permissions(self, client, board):
        response = client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        assert response.status_code == HTTPStatus.FOUND

    def test_other_user_permissions(self, client, user2, board):
        client.force_login(user2)
        response = client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_owner_permissions(self, client, board, user):
        client.force_login(user)
        response = client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        assert response.status_code == HTTPStatus.OK

    def test_staff_permissions(self, client, board, user_staff):
        client.force_login(user_staff)
        response = client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        assert response.status_code == HTTPStatus.OK

    def test_board_update_success(self, client, board, user):
        client.force_login(user)
        response = client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {
                "title": "Test Board NEW",
                "description": "Test Board Description NEW",
            },
        )
        assert response.status_code == HTTPStatus.OK
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
        assert response.status_code == HTTPStatus.OK
        assertFormError(response.context["form"], "title", "This field is required.")

    def test_board_update_invalid(self, client, board, user):
        client.force_login(user)
        response = client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {"title": "x" * 51, "description": "x" * 101},
        )
        assert response.status_code == HTTPStatus.OK
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
    @pytest.fixture()
    def get_board_delete_url(self, board):
        return reverse("boards:board-delete", kwargs={"slug": board.slug})

    @pytest.mark.parametrize(
        ("test_user", "expected_response_get", "expected_response_post"),
        [
            (None, HTTPStatus.FOUND, HTTPStatus.FOUND),
            (lf("user2"), HTTPStatus.FORBIDDEN, HTTPStatus.FORBIDDEN),
            (lf("user"), HTTPStatus.OK, HTTPStatus.FOUND),
            (lf("user_staff"), HTTPStatus.OK, HTTPStatus.FOUND),
        ],
    )
    def test_permissions(
        self, client, test_user, expected_response_get, expected_response_post, get_board_delete_url
    ):
        if test_user:
            client.force_login(test_user)
        response_get = client.get(get_board_delete_url)
        assert response_get.status_code == expected_response_get
        response_post = client.post(get_board_delete_url)
        assert response_post.status_code == expected_response_post
        if expected_response_get == HTTPStatus.OK:
            assert response_post.url == "/boards/"
        elif expected_response_get == HTTPStatus.FOUND:
            assert response_post.url == f"/accounts/login/?next={get_board_delete_url}"

    def test_delete_board_with_reactions(self, client, board, user, reaction_factory, get_board_delete_url):
        client.force_login(user)
        reaction_factory(post__topic__board=board)
        assert len(Reaction.objects.all()) == 1
        response = client.get(get_board_delete_url)
        assert response.status_code == HTTPStatus.OK
        response = client.post(get_board_delete_url)
        assert response.status_code == HTTPStatus.FOUND
        assert len(Reaction.objects.all()) == 0


class TestImageSelectView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, image_factory):
        for image_type, _ in IMAGE_TYPE:
            image_factory.create_batch(5, board=board if image_type == "p" else None, image_type=image_type)

    @pytest.mark.parametrize(
        ("test_user", "expected_response"),
        [
            (None, HTTPStatus.FOUND),
            (lf("user"), HTTPStatus.OK),
        ],
    )
    @pytest.mark.parametrize("image_type", [image_type[0] for image_type in IMAGE_TYPE])
    def test_image_select(self, client, test_user, expected_response, image_type):
        if test_user:
            client.force_login(test_user)
        response = client.get(reverse("boards:image-select", kwargs={"image_type": image_type}))
        assert response.status_code == expected_response

        if expected_response == HTTPStatus.OK:
            assert response.context["images"].count() == Image.objects.filter(image_type=image_type).count()
        else:
            assert response.url == f"/accounts/login/?next=/boards/image_select/{image_type}/"


class TestQrView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, user3):
        board.preferences.moderators.add(user3)
        board.preferences.save()

    @pytest.mark.parametrize(
        ("test_user", "expected_response"),
        [
            (None, HTTPStatus.FOUND),
            (lf("user2"), HTTPStatus.FORBIDDEN),
            (lf("user"), HTTPStatus.OK),
            (lf("user3"), HTTPStatus.OK),
            (lf("user_staff"), HTTPStatus.OK),
        ],
    )
    def test_qr_permissions(self, client, board, test_user, expected_response):
        if test_user:
            client.force_login(test_user)
        response = client.get(reverse("boards:board-qr", kwargs={"slug": board.slug}))
        assert response.status_code == expected_response
        if expected_response == HTTPStatus.FOUND:
            assert response.url == f"/accounts/login/?next=/boards/{board.slug}/qr/"
