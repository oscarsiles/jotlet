from django.test import TestCase

from accounts.tests.factories import UserFactory
from boards.forms import BoardPreferencesForm, SearchBoardsForm
from boards.models import Post
from boards.tests.factories import BoardFactory, PostFactory, TopicFactory

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
        cls.user = UserFactory(username="test_user")  # username to match test form data
        cls.board = BoardFactory(slug="000001")

    def test_board_preferences_form_valid(self):
        form_data = TEST_FORM_DATA
        form = BoardPreferencesForm(data=form_data, board=self.board, instance=self.board.preferences)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.helper.attrs["hx-post"], "/boards/000001/preferences/")
        form.save()
        self.assertEqual(self.board.preferences.background_type, form_data.get("background_type"))
        self.assertEqual(self.board.preferences.background_color, form_data.get("background_color"))
        self.assertEqual(self.board.preferences.background_opacity, form_data.get("background_opacity"))
        self.assertEqual(self.board.preferences.require_post_approval, form_data.get("require_post_approval"))
        self.assertEqual(self.board.preferences.enable_latex, form_data.get("enable_latex"))
        self.assertEqual(self.board.preferences.moderators.count(), 1)
        self.assertEqual(self.board.preferences.moderators.all()[0], self.user)
        self.assertEqual(self.board.preferences.reaction_type, form_data.get("reaction_type"))

    def test_board_preferences_form_approve_all(self):
        form_data = TEST_FORM_DATA
        form_data["require_post_approval"] = True
        form = BoardPreferencesForm(data=form_data, board=self.board, instance=self.board.preferences)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(self.board.preferences.require_post_approval, True)
        topic = TopicFactory(board=self.board)
        for i in range(5):
            post = PostFactory(topic=topic, approved=False)
            self.assertEqual(post.approved, False)

        self.assertEqual(Post.objects.filter(approved=True).count(), 0)
        form_data["require_post_approval"] = False
        form = BoardPreferencesForm(data=form_data, board=self.board, instance=self.board.preferences)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Post.objects.filter(approved=True).count(), 5)

    def test_board_preferences_form_invalid(self):
        form_data = {
            "background_type": "x",
            "background_color": "fffffffff",
            "background_opacity": "2.0",
        }
        form = BoardPreferencesForm(data=form_data, board=self.board, instance=self.board.preferences)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["background_type"], ["Select a valid choice. x is not one of the available choices."]
        )
        self.assertEqual(form.errors["background_color"], ["Ensure this value has at most 7 characters (it has 9)."])
        self.assertEqual(form.errors["background_opacity"], ["Value needs to be between 0.0 and 1.0."])


class SearchBoardsFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        BoardFactory(slug="123456ab")

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
