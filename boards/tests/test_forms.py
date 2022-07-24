from django.contrib.auth.models import User
from django.test import TestCase

from boards.forms import BoardPreferencesForm, SearchBoardsForm
from boards.models import Board, Post, Topic

TEST_FORM_DATA = {
    "type": "d",
    "background_type": "c",
    "background_color": "#123456",
    "background_image": None,
    "background_opacity": 0.5,
    "require_post_approval": True,
    "allow_guest_replies": True,
    "enable_latex": True,
    "moderators": "test_user,non_existent_user",
    "reaction_type": "v",
}


class BoardPreferencesFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(username="test_user", password="test_password")
        Board.objects.create(title="Test Board", slug="000001")

    def test_board_preferences_form_valid(self):
        board = Board.objects.get(slug="000001")
        form_data = TEST_FORM_DATA
        form = BoardPreferencesForm(data=form_data, board=board, instance=board.preferences)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.helper.attrs["hx-post"], "/boards/000001/preferences/")
        form.save()
        board = Board.objects.prefetch_related("preferences").get(slug="000001")
        self.assertEqual(board.preferences.background_type, form_data.get("background_type"))
        self.assertEqual(board.preferences.background_color, form_data.get("background_color"))
        self.assertEqual(board.preferences.background_opacity, form_data.get("background_opacity"))
        self.assertEqual(board.preferences.require_post_approval, form_data.get("require_post_approval"))
        self.assertEqual(board.preferences.enable_latex, form_data.get("enable_latex"))
        self.assertEqual(board.preferences.moderators.count(), 1)
        self.assertEqual(board.preferences.moderators.all()[0], User.objects.get(username="test_user"))
        self.assertEqual(board.preferences.reaction_type, form_data.get("reaction_type"))

    def test_board_preferences_form_approve_all(self):
        board = Board.objects.get(slug="000001")
        form_data = TEST_FORM_DATA
        form_data["require_post_approval"] = True
        form = BoardPreferencesForm(data=form_data, board=board, instance=board.preferences)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(board.preferences.require_post_approval, True)
        topic = Topic.objects.create(board=board, subject="Test Topic")
        for i in range(5):
            post = Post.objects.create(topic=topic, content=f"Test Post {i}", approved=False)
            self.assertEqual(post.approved, False)

        form_data["require_post_approval"] = False
        form = BoardPreferencesForm(data=form_data, board=board, instance=board.preferences)
        self.assertTrue(form.is_valid())
        form.save()
        for i in range(5):
            self.assertEqual(Post.objects.get(content=f"Test Post {i}").approved, True)

    def test_board_preferences_form_invalid(self):
        board = Board.objects.get(slug="000001")
        form_data = {
            "background_type": "x",
            "background_color": "fffffffff",
            "background_opacity": "2.0",
        }
        form = BoardPreferencesForm(data=form_data, board=board, instance=board.preferences)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["background_type"], ["Select a valid choice. x is not one of the available choices."]
        )
        self.assertEqual(form.errors["background_color"], ["Ensure this value has at most 7 characters (it has 9)."])
        self.assertEqual(form.errors["background_opacity"], ["Value needs to be between 0.0 and 1.0."])


class SearchBoardsFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Board.objects.create(title="Test Board", slug="123456ab")

    def test_search_boards_form_valid(self):
        form_data = {
            "board_slug": "123456ab",
        }
        form = SearchBoardsForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_search_clean_board_slug(self):
        form_data = {
            "board_slug": " 12 34-56-ab",
        }
        form = SearchBoardsForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["board_slug"], "123456ab")

    def test_search_boards_form_invalid(self):
        form_data = {
            "board_slug": "x",
        }
        form = SearchBoardsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["board_slug"], ["ID should be 6 or 8 lowercase letters and/or digits."])

    def test_search_boards_form_not_exist(self):
        form_data = {
            "board_slug": "000000ab",
        }
        form = SearchBoardsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["board_slug"], ["Board does not exist."])
