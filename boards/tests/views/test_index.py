import math
from http import HTTPStatus

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from pytest_django.asserts import assertFormError, assertTemplateUsed

from boards.views.index import BoardListView


class TestIndexView:
    def test_anonymous_permissions(self, client):
        response = client.get(reverse("boards:index"))
        assert response.status_code == HTTPStatus.OK

    def test_board_search_success(self, client, board):
        response = client.post(reverse("boards:index"), {"board_slug": board.slug})
        assert response.status_code == HTTPStatus.FOUND

    def test_board_search_invalid(self, client):
        response = client.post(reverse("boards:index"), {"board_slug": "invalid"})
        assert response.status_code == HTTPStatus.OK
        assertFormError(response.context["form"], "board_slug", "ID should be 6 or 8 letters and/or digits.")

    def test_board_search_not_found(self, client, board):
        board.slug = "00000001"
        board.save()
        response = client.post(reverse("boards:index"), {"board_slug": "000000"})
        assert response.status_code == HTTPStatus.OK
        assertFormError(response.context["form"], "board_slug", "Board does not exist.")

    def test_board_search_no_slug(self, client):
        response = client.post(reverse("boards:index"))
        assert response.status_code == HTTPStatus.OK
        assertFormError(response.context["form"], "board_slug", "This field is required.")


class TestIndexAllBoardsView:
    def test_anonymous_all_boards(self, client):
        response = client.get(reverse("boards:index-all"))
        assert response.status_code == HTTPStatus.FOUND

    def test_board_non_staff_all_boards(self, client, user):
        client.force_login(user)
        response = client.get(reverse("boards:index-all"))
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_board_staff_all_boards(self, client, user_staff):
        client.force_login(user_staff)
        response = client.get(reverse("boards:index-all"))
        assert response.status_code == HTTPStatus.OK


# TODO: Implement further tests for all board_list_types
class TestBoardListView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, user, user2, board_factory, user_factory):
        self.user_board_count = 10
        self.user_mod_board_count = 5
        self.user2_board_count = 25
        self.total_posts = self.user_board_count + self.user_mod_board_count + self.user2_board_count
        self.default_paginate_by = user.profile.boards_paginate_by
        board_factory.create_batch(self.user_board_count, owner=user)
        board_factory.create_batch(self.user2_board_count, owner=user2)
        mod_boards = board_factory.create_batch(self.user_mod_board_count, owner=user2)
        for board in mod_boards:
            board.preferences.moderators.add(user)
            board.preferences.save()

    def test_anonymous_permissions(self, client):
        response = client.get(reverse("boards:board-list", kwargs={"board_list_type": "own"}))
        assert response.status_code == HTTPStatus.FOUND

    def test_user_index(self, client, user):
        client.force_login(user)
        response = client.get(
            reverse("boards:board-list", kwargs={"board_list_type": "own"}),
            {},
            HTTP_REFERER=reverse("boards:index"),
        )
        assert response.status_code == HTTPStatus.OK
        assertTemplateUsed(response, "boards/components/board_list.html")
        assert len(response.context["boards"]) == self.user_board_count

    @pytest.mark.parametrize(
        ("board_list_type", "expected_board_count"),
        [
            ("own", 10),
            ("mod", 5),
            ("all", 10),
        ],
    )
    def test_user_no_perm_all_boards(self, client, user, board_list_type, expected_board_count):
        client.force_login(user)
        response = client.get(
            reverse("boards:board-list", kwargs={"board_list_type": board_list_type}),
            {},
            HTTP_REFERER=reverse("boards:index-all"),
        )
        assert response.status_code == HTTPStatus.OK
        assertTemplateUsed(response, "boards/components/board_list.html")
        assert len(response.context["boards"]) == expected_board_count

    @pytest.mark.parametrize(
        ("data", "page"),
        [
            ({}, 1),
            ({"page": 2}, 2),
        ],
    )
    def test_user_perm_all_boards(self, client, user, data, page):
        user.user_permissions.add(Permission.objects.get(codename="can_view_all_boards"))
        user.save()
        client.force_login(user)
        response = client.get(
            reverse("boards:board-list", kwargs={"board_list_type": "all"}),
            data,
            HTTP_REFERER=reverse("boards:index-all"),
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.context["boards"]) == user.profile.boards_paginate_by

        assertTemplateUsed(response, "boards/components/board_list.html")
        assert len(response.context["boards"]) == user.profile.boards_paginate_by
        assert response.context["page_obj"].number == page
        assert len(response.context["page_obj"].paginator.page_range) == math.ceil(
            self.total_posts / self.default_paginate_by
        )

    @pytest.mark.parametrize("paginate_by", [None, 3, 5, 10, 20])
    def test_paginate_by_userprofile(self, rf, user, paginate_by):
        if paginate_by is not None:
            user.profile.boards_paginate_by = paginate_by
            user.profile.save()
            user.refresh_from_db()
        expected_page_range = math.ceil(self.user_board_count / user.profile.boards_paginate_by)

        request = rf.get(reverse("boards:board-list", kwargs={"board_list_type": "own"}))
        request.user = user
        response = BoardListView.as_view()(request, board_list_type="own")
        assert response.status_code == HTTPStatus.OK
        assert (
            request.user.profile.boards_paginate_by == paginate_by
            if paginate_by is not None
            else self.default_paginate_by
        )
        assert (
            response.context_data["paginate_by"] == paginate_by
            if paginate_by is not None
            else self.default_paginate_by
        )
        assert response.context_data["page_obj"].number == 1
        assert len(response.context_data["page_obj"].paginator.page_range) == expected_page_range

    @pytest.mark.parametrize(
        ("paginate_by", "page_range"),
        [
            (10, 1),
            (20, 1),
            (5, 2),
        ],
    )
    def test_paginate_by_querystring(self, rf, user, paginate_by, page_range):
        request = rf.get(
            reverse("boards:board-list", kwargs={"board_list_type": "own"}),
            {"paginate_by": paginate_by},
        )
        request.user = user
        response = BoardListView.as_view()(request, board_list_type="own")
        assert response.status_code == HTTPStatus.OK
        assert request.user.profile.boards_paginate_by == paginate_by
        assert response.context_data["paginate_by"] == paginate_by
        assert response.context_data["page_obj"].number == 1
        assert len(response.context_data["page_obj"].paginator.page_range) == page_range
