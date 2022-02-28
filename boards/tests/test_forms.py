from django.test import TestCase

from boards.forms import BoardPreferencesForm, SearchBoardsForm
from boards.models import Board


class BoardPreferencesFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        pass

    def test_board_preferences_form_valid(self):
        form_data = {
            "background_type": "c",
            "background_color": "#ffffff",
            "background_image": None,
            "background_opacity": "0.5",
            "require_approval": True,
            "enable_latex": True,
        }
        form = BoardPreferencesForm(data=form_data, slug="random_slug")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.helper.attrs["hx-post"], "/boards/random_slug/preferences/")

    def test_board_preferences_form_invalid(self):
        form_data = {
            "slug": "1",
            "background_type": "x",
            "background_color": "fffffffff",
            "background_opacity": "2.0",
        }
        form = BoardPreferencesForm(data=form_data, slug="1")
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
