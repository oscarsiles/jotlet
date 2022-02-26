from django.test import TestCase
from django.urls import reverse

from django.contrib.auth.models import User

from django_fakeredis import FakeRedis

from boards.models import Board, Topic, Post


class IndexBoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        Board.objects.create(title="Test Board", description="Test Board Description", owner=test_user1)

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:index"))
        self.assertEqual(response.status_code, 200)

    def test_board_search_success(self):
        board = Board.objects.get(id=1)
        response = self.client.post(reverse("boards:index"), {"board_slug": board.slug})
        self.assertEqual(response.status_code, 302)

    def test_board_search_invalid(self):
        response = self.client.post(reverse("boards:index"), {"board_slug": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "board_slug", "ID format needs to be ######.")

    def test_board_search_not_found(self):
        board = Board.objects.get(id=1)
        bad_slug = "000000" if board.slug != "000000" else "111111"
        response = self.client.post(reverse("boards:index"), {"board_slug": bad_slug})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "board_slug", "Board does not exist.")

    def test_board_search_no_slug(self):
        response = self.client.post(reverse("boards:index"), {})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "board_slug", "This field is required.")

    def test_board_non_staff_all_boards(self):
        self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("boards:index"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context.get("all_boards"))

    def test_board_staff_all_boards(self):
        test_user2 = User.objects.create_user(username="testuser2", password="1X<ISRUkw+tuK", is_staff=True)
        for i in range(10):
            Board.objects.create(title=f"Test Board {i}", description=f"Test Board Description {i}", owner=test_user2)
        login = self.client.login(username="testuser2", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("boards:index"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context.get("all_boards"))
        self.assertEqual(len(response.context.get("all_boards")), 11)


class CreateBoardViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:board-create"))
        self.assertEqual(response.status_code, 302)

    def test_user_permissions(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.get(reverse("boards:board-create"))
        self.assertEqual(str(response.context["user"]), "testuser1")
        self.assertEqual(response.status_code, 200)

    def test_board_create_success(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(
            reverse("boards:board-create"), {"title": "Test Board", "description": "Test Board Description"}
        )
        self.assertEqual(response.status_code, 302)
        board = Board.objects.get(title="Test Board")
        self.assertEqual(board.description, "Test Board Description")

    def test_board_create_blank(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        response = self.client.post(reverse("boards:board-create"), {"title": "", "description": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "title", "This field is required.")
        self.assertFormError(response, "form", "description", "This field is required.")

    def test_board_create_invalid(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
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
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)

    def test_anonymous_permissions(self):
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_staff_permissions(self):
        staff_user = User.objects.create_user(username="staff", password="83jKJ+!fdjP", is_staff=True)
        login = self.client.login(username="staff", password="83jKJ+!fdjP")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-update", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_board_update_success(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {"title": "Test Board NEW", "description": "Test Board Description NEW"},
        )
        self.assertEqual(response.status_code, 302)
        board = Board.objects.get(id=1)
        self.assertEqual(board.title, "Test Board NEW")
        self.assertEqual(board.description, "Test Board Description NEW")

    def test_board_update_blank(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.post(
            reverse("boards:board-update", kwargs={"slug": board.slug}),
            {"title": "", "description": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "title", "This field is required.")
        self.assertFormError(response, "form", "description", "This field is required.")

    def test_board_create_invalid(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
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
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)

    def test_anonymous_permissions(self):
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        login = self.client.login(username="testuser2", password="2HJ1vRV0Z&3iD")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        login = self.client.login(username="testuser1", password="1X<ISRUkw+tuK")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Board.objects.all()), 0)

    def test_staff_permissions(self):
        staff_user = User.objects.create_user(username="staff", password="83jKJ+!fdjP", is_staff=True)
        login = self.client.login(username="staff", password="83jKJ+!fdjP")
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("boards:board-delete", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(Board.objects.all()), 0)


class BoardViewTest(TestCase):
    @classmethod
    @FakeRedis("django.core.cache.cache")
    def setUpTestData(cls):
        test_user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        test_user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        Board.objects.create(title="Test Board", description="Test Description", owner=test_user1)

    def test_anonymous_permissions(self):
        board = Board.objects.get(id=1)
        response = self.client.get(reverse("boards:board", kwargs={"slug": board.slug}))
        self.assertEqual(response.status_code, 200)
