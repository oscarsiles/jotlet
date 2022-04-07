from django.contrib.auth.models import User
from django.test import TestCase

from boards.forms import BoardPreferencesForm, SearchBoardsForm
from boards.models import Board


class BoardPreferencesFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(username="test_user", password="test_password")
        Board.objects.create(title="Test Board", slug="test_board")

    def test_board_preferences_form_valid(self):
        board = Board.objects.get(slug="test_board")
        form_data = {
            "background_type": "c",
            "background_color": "#123456",
            "background_image": None,
            "background_opacity": "0.5",
            "require_approval": True,
            "enable_latex": True,
            "moderators": "test_user,non_existent_user",
            "reaction_type": "v",
        }
        form = BoardPreferencesForm(data=form_data, slug="test_board", instance=board.preferences)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.helper.attrs["hx-post"], "/boards/test_board/preferences/")
        form.save()
        board = Board.objects.get(slug="test_board")
        self.assertEqual(board.preferences.background_type, "c")
        self.assertEqual(board.preferences.background_color, "#123456")
        self.assertEqual(board.preferences.background_opacity, 0.5)
        self.assertEqual(board.preferences.require_approval, True)
        self.assertEqual(board.preferences.enable_latex, True)
        self.assertEqual(board.preferences.moderators.count(), 1)
        self.assertEqual(board.preferences.moderators.all()[0], User.objects.get(username="test_user"))
        self.assertEqual(board.preferences.reaction_type, "v")
        form = BoardPreferencesForm(data=form_data, slug="test_board", instance=board.preferences)
        self.assertTrue(form.is_valid())
        form.save()

    def test_board_preferences_form_invalid(self):
        board = Board.objects.get(slug="test_board")
        form_data = {
            "background_type": "x",
            "background_color": "fffffffff",
            "background_opacity": "2.0",
        }
        form = BoardPreferencesForm(data=form_data, slug="test_board", instance=board.preferences)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["background_type"], ["Select a valid choice. x is not one of the available choices."]
        )
        self.assertEqual(form.errors["background_color"], ["Ensure this value has at most 7 characters (it has 9)."])
        self.assertEqual(form.errors["background_opacity"], ["Value needs to be between 0.0 and 1.0."])


class SearchBoardsFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Board.objects.create(title="Test Board", slug="123456")

    def test_search_boards_form_valid(self):
        form_data = {
            "board_slug": "123456",
        }
        form = SearchBoardsForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_search_clean_board_slug(self):
        form_data = {
            "board_slug": " 12 34-56-",
        }
        form = SearchBoardsForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["board_slug"], "123456")

    def test_search_boards_form_invalid(self):
        form_data = {
            "board_slug": "x",
        }
        form = SearchBoardsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["board_slug"], ["ID format needs to be ######."])

    def test_search_boards_form_not_exist(self):
        form_data = {
            "board_slug": "000000",
        }
        form = SearchBoardsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["board_slug"], ["Board does not exist."])
