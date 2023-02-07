import pytest
from django.contrib.auth.models import Permission
from django.templatetags.static import static
from django.urls import reverse
from pytest_django.asserts import assertFormError, assertTemplateUsed

from boards.views.index import BoardListView


class TestIndexView:
    def test_anonymous_permissions(self, client):
        response = client.get(reverse("boards:index"))
        assert response.status_code == 200

    def test_board_search_success(self, client, board):
        response = client.post(reverse("boards:index"), {"board_slug": board.slug})
        assert response.status_code == 302

    def test_board_search_invalid(self, client):
        response = client.post(reverse("boards:index"), {"board_slug": "invalid"})
        assert response.status_code == 200
        assertFormError(response.context["form"], "board_slug", "ID should be 6 or 8 letters and/or digits.")

    def test_board_search_not_found(self, client, board):
        board.slug = "00000001"
        board.save()
        response = client.post(reverse("boards:index"), {"board_slug": "000000"})
        assert response.status_code == 200
        assertFormError(response.context["form"], "board_slug", "Board does not exist.")

    def test_board_search_no_slug(self, client):
        response = client.post(reverse("boards:index"))
        assert response.status_code == 200
        assertFormError(response.context["form"], "board_slug", "This field is required.")

    def test_link_headers_staff(self, client, user_staff):
        client.force_login(user_staff)
        response = client.get(reverse("boards:index"))
        link_header = response.get("Link")
        assert link_header is not None
        assert f"<{static('css/vendor/bootstrap-5.3.0-alpha1.min.css')}>; rel=preload; as=style" in link_header
        assert f"<{static('boards/js/index.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('boards/js/components/board_list.js')}>; rel=preload; as=script" in link_header
        assert "css/vendor/tagify-4.17.7.min.css" not in link_header

    def test_link_headers_anonymous(self, client):
        response = client.get(reverse("boards:index"))
        link_header = response.get("Link")
        assert link_header is not None
        assert f"<{static('css/vendor/bootstrap-5.3.0-alpha1.min.css')}>; rel=preload; as=style" in link_header
        assert f"<{static('boards/js/index.js')}>; rel=preload; as=script" in link_header
        assert "boards/js/components/board_list.js" not in link_header


class TestIndexAllBoardsView:
    def test_anonymous_all_boards(self, client):
        response = client.get(reverse("boards:index-all"))
        assert response.status_code == 302

    def test_board_non_staff_all_boards(self, client, user):
        client.force_login(user)
        response = client.get(reverse("boards:index-all"))
        assert response.status_code == 403

    def test_board_staff_all_boards(self, client, user_staff):
        client.force_login(user_staff)
        response = client.get(reverse("boards:index-all"))
        assert response.status_code == 200

    def test_link_headers(self, client, user_staff):
        client.force_login(user_staff)
        response = client.get(reverse("boards:index-all"))
        link_header = response.get("Link")
        assert link_header is not None
        assert f"<{static('css/vendor/bootstrap-5.3.0-alpha1.min.css')}>; rel=preload; as=style" in link_header
        assert f"<{static('boards/js/index.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('boards/js/components/board_list.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('css/vendor/tagify-4.17.7.min.css')}>; rel=preload; as=style" in link_header


# TODO: Implement further tests for all board_list_types
class TestBoardListView:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, user, user2, board_factory):
        board_factory.create_batch(10, owner=user)
        board_factory.create_batch(10, owner=user2)

    def test_anonymous_permissions(self, client):
        response = client.get(reverse("boards:board-list", kwargs={"board_list_type": "own"}))
        assert response.status_code == 302

    def test_user_index(self, client, user):
        client.force_login(user)
        response = client.get(
            reverse("boards:board-list", kwargs={"board_list_type": "own"}), {}, HTTP_REFERER=reverse("boards:index")
        )
        assert response.status_code == 200
        assertTemplateUsed(response, "boards/components/board_list.html")
        assert len(response.context["boards"]) == 10

    def test_user_no_perm_all_boards(self, client, user):
        client.force_login(user)
        response = client.get(
            reverse("boards:board-list", kwargs={"board_list_type": "own"}),
            {},
            HTTP_REFERER=reverse("boards:index-all"),
        )
        assert response.status_code == 200
        assertTemplateUsed(response, "boards/components/board_list.html")
        assert len(response.context["boards"]) == 10

    @pytest.mark.parametrize(
        "dict,page",
        [
            ({}, 1),
            ({"page": 2}, 2),
        ],
    )
    def test_user_perm_all_boards(self, client, user, dict, page):
        user.user_permissions.add(Permission.objects.get(codename="can_view_all_boards"))
        user.save()
        client.force_login(user)
        response = client.get(
            reverse("boards:board-list", kwargs={"board_list_type": "all"}),
            dict,
            HTTP_REFERER=reverse("boards:index-all"),
        )
        assert response.status_code == 200
        assertTemplateUsed(response, "boards/components/board_list.html")
        assert len(response.context["boards"]) == 10
        assert response.context["page_obj"].number == page
        assert len(response.context["page_obj"].paginator.page_range) == 2

    @pytest.mark.parametrize(
        "paginate_by,page_range",
        [
            (None, 1),
            (10, 1),
            (20, 1),
            (5, 2),
        ],
    )
    def test_paginate_by_userprofile(self, rf, user, paginate_by, page_range):
        if paginate_by is not None:
            user.profile.boards_paginate_by = paginate_by
            user.profile.save()
        request = rf.get(reverse("boards:board-list", kwargs={"board_list_type": "own"}))
        request.user = user
        response = BoardListView.as_view()(request, board_list_type="own")
        assert response.status_code == 200
        assert request.user.profile.boards_paginate_by == paginate_by if paginate_by is not None else 10
        assert response.context_data["paginate_by"] == paginate_by if paginate_by is not None else 10
        assert response.context_data["page_obj"].number == 1
        assert len(response.context_data["page_obj"].paginator.page_range) == page_range

    @pytest.mark.parametrize(
        "paginate_by,page_range",
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
        assert response.status_code == 200
        assert request.user.profile.boards_paginate_by == paginate_by
        assert response.context_data["paginate_by"] == paginate_by
        assert response.context_data["page_obj"].number == 1
        assert len(response.context_data["page_obj"].paginator.page_range) == page_range
