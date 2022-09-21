from django.contrib.auth.models import Permission
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from accounts.tests.factories import USER_TEST_PASSWORD, UserFactory
from boards.tests.factories import BoardFactory
from boards.tests.utils import create_session
from boards.views.index import BoardListView


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


# TODO: Implement further tests for all board_list_types
class BoardListViewTest(TestCase):
    @classmethod
    def setUp(cls):
        cls.factory = RequestFactory()

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        BoardFactory.create_batch(10, owner=cls.user)
        BoardFactory.create_batch(10, owner=cls.user2)

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
        self.assertEqual(len(response.context["boards"]), 10)

    def test_user_no_perm_all_boards(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:board-list", kwargs={"board_list_type": "own"}),
            {},
            HTTP_REFERER=reverse("boards:index-all"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "boards/components/board_list.html")
        self.assertEqual(len(response.context["boards"]), 10)

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
        self.assertEqual(len(response.context["boards"]), 10)
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
        self.assertEqual(len(response.context["boards"]), 10)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["page_obj"].paginator.page_range), 2)

    def test_paginate_by_session(self):
        request = self.factory.get(reverse("boards:board-list", kwargs={"board_list_type": "own"}))
        request.user = self.user
        create_session(request)
        response = BoardListView.as_view()(request, board_list_type="own")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(request.session.get("paginate_by"))
        self.assertEqual(response.context_data["paginate_by"], 10)
        self.assertEqual(response.context_data["page_obj"].number, 1)
        self.assertEqual(len(response.context_data["page_obj"].paginator.page_range), 1)

        request = self.factory.get(reverse("boards:board-list", kwargs={"board_list_type": "own"}))
        request.user = self.user
        create_session(request)
        request.session["paginate_by"] = 20
        request.session.save()
        response = BoardListView.as_view()(request, board_list_type="own")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.session.get("paginate_by"), 20)
        self.assertEqual(response.context_data["paginate_by"], 20)
        self.assertEqual(response.context_data["page_obj"].number, 1)
        self.assertEqual(len(response.context_data["page_obj"].paginator.page_range), 1)

        request = self.factory.get(reverse("boards:board-list", kwargs={"board_list_type": "own"}))
        request.user = self.user
        create_session(request)
        request.session["paginate_by"] = 5
        request.session.save()
        response = BoardListView.as_view()(request, board_list_type="own")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.session.get("paginate_by"), 5)
        self.assertEqual(response.context_data["paginate_by"], 5)
        self.assertEqual(response.context_data["page_obj"].number, 1)
        self.assertEqual(len(response.context_data["page_obj"].paginator.page_range), 2)

    def test_paginate_by_querystring(self):
        request = self.factory.get(
            reverse("boards:board-list", kwargs={"board_list_type": "own"}),
            {"paginate_by": 20},
        )
        request.user = self.user
        create_session(request)
        response = BoardListView.as_view()(request, board_list_type="own")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.session.get("paginate_by"), 20)
        self.assertEqual(response.context_data["paginate_by"], 20)
        self.assertEqual(response.context_data["page_obj"].number, 1)
        self.assertEqual(len(response.context_data["page_obj"].paginator.page_range), 1)

        request = self.factory.get(
            reverse("boards:board-list", kwargs={"board_list_type": "own"}),
            {"paginate_by": 5},
        )
        request.user = self.user
        create_session(request)
        response = BoardListView.as_view()(request, board_list_type="own")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.session.get("paginate_by"), 5)
        self.assertEqual(response.context_data["paginate_by"], 5)
        self.assertEqual(response.context_data["page_obj"].number, 1)
        self.assertEqual(len(response.context_data["page_obj"].paginator.page_range), 2)
