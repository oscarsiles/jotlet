from boards.forms import BoardPreferencesForm, SearchBoardsForm
from boards.models import Post

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


class TestBoardPreferencesForm:
    def test_board_preferences_form_valid(self, board, user):
        user.username = "test_user"
        user.save()
        form_data = TEST_FORM_DATA
        form = BoardPreferencesForm(data=form_data, board=board, instance=board.preferences)
        assert form.is_valid()
        assert form.helper.attrs["hx-post"] == f"/boards/{board.slug}/preferences/"
        form.save()
        assert board.preferences.background_type == form_data.get("background_type")
        assert board.preferences.background_color == form_data.get("background_color")
        assert board.preferences.background_opacity == form_data.get("background_opacity")
        assert board.preferences.require_post_approval == form_data.get("require_post_approval")
        assert board.preferences.enable_latex == form_data.get("enable_latex")
        assert board.preferences.moderators.count() == 1
        assert board.preferences.moderators.all()[0] == user
        assert board.preferences.reaction_type == form_data.get("reaction_type")

    def test_board_preferences_form_approve_all(self, board, topic, post_factory):
        form_data = TEST_FORM_DATA
        form_data["require_post_approval"] = True
        form = BoardPreferencesForm(data=form_data, board=board, instance=board.preferences)
        assert form.is_valid()
        form.save()
        assert board.preferences.require_post_approval is True
        post_factory.create_batch(5, topic=topic, approved=False)

        assert Post.objects.filter(approved=True).count() == 0
        form_data["require_post_approval"] = False
        form = BoardPreferencesForm(data=form_data, board=board, instance=board.preferences)
        assert form.is_valid()
        form.save()
        assert Post.objects.filter(approved=True).count() == 5

    def test_board_preferences_form_invalid(self, board):
        form_data = {
            "background_type": "x",
            "background_color": "fffffffff",
            "background_opacity": "2.0",
        }
        form = BoardPreferencesForm(data=form_data, board=board, instance=board.preferences)
        assert not form.is_valid()
        assert form.errors["background_type"] == ["Select a valid choice. x is not one of the available choices."]
        assert form.errors["background_color"] == ["Ensure this value has at most 7 characters (it has 9)."]
        assert form.errors["background_opacity"] == ["Value needs to be between 0.0 and 1.0."]


class TestSearchBoardsForm:
    def test_search_boards_form_valid(self, board):
        form_data = {
            "board_slug": f"{board.slug}",
        }
        form = SearchBoardsForm(data=form_data)
        assert form.is_valid()

    def test_search_clean_board_slug(self, board):
        board.slug = "123456ab"
        board.save()
        form_data = {
            "board_slug": " 12 34-56-ab",
        }
        form = SearchBoardsForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data["board_slug"] == "123456ab"

    def test_search_boards_form_invalid(self):
        form_data = {
            "board_slug": "x",
        }
        form = SearchBoardsForm(data=form_data)
        assert not form.is_valid()
        assert form.errors["board_slug"] == ["ID should be 6 or 8 lowercase letters and/or digits."]

    def test_search_boards_form_not_exist(self, board):
        test_slug = "123456ab" if board.slug != "123456ab" else "123456cd"
        form_data = {"board_slug": test_slug}
        form = SearchBoardsForm(data=form_data)
        assert not form.is_valid()
        assert form.errors["board_slug"] == ["Board does not exist."]
