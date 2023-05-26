import json

import pytest
from pytest_lazyfixture import lazy_fixture

from boards.forms import BoardPreferencesForm, BoardSearchForm, PostCreateForm
from boards.models import ADDITIONAL_DATA_TYPE, Post

BOARD_PREFERENCES_FORM_DATA = {
    "board_type": "d",
    "background_type": "c",
    "background_color": "#123456",
    "background_image": None,
    "background_opacity": 0.5,
    "require_post_approval": True,
    "allow_guest_replies": True,
    "enable_latex": True,
    "enable_chemdoodle": True,
    "moderators": "test_user,non_existent_user",
    "reaction_type": "v",
}

ADDITIONAL_DATA_TYPE_CHOICES = [choice[0] for choice in ADDITIONAL_DATA_TYPE]


class TestBoardPreferencesForm:
    def test_board_preferences_form_valid(self, board, user):
        user.username = "test_user"
        user.save()
        form_data = BOARD_PREFERENCES_FORM_DATA
        form = BoardPreferencesForm(data=form_data, board=board, instance=board.preferences)
        assert form.is_valid()
        assert form.helper.attrs["hx-post"] == f"/boards/{board.slug}/preferences/"
        form.save()
        assert board.preferences.background_type == form_data.get("background_type")
        assert board.preferences.background_color == form_data.get("background_color")
        assert board.preferences.background_opacity == form_data.get("background_opacity")
        assert board.preferences.require_post_approval == form_data.get("require_post_approval")
        assert board.preferences.enable_latex == form_data.get("enable_latex")
        assert board.preferences.enable_chemdoodle == form_data.get("enable_chemdoodle")
        assert board.preferences.moderators.count() == 1
        assert board.preferences.moderators.all()[0] == user
        assert board.preferences.reaction_type == form_data.get("reaction_type")

    def test_board_preferences_form_approve_all(self, board, topic, post_factory):
        form_data = BOARD_PREFERENCES_FORM_DATA
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


class TestBoardSearchForm:
    def test_search_boards_form_valid(self, board):
        form_data = {
            "board_slug": f"{board.slug}",
        }
        form = BoardSearchForm(data=form_data)
        assert form.is_valid()

    def test_search_clean_board_slug(self, board):
        board.slug = "123456ab"
        board.save()
        form_data = {
            "board_slug": " 12 34-56-ab",
        }
        form = BoardSearchForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data["board_slug"] == "123456ab"

    def test_search_clean_board_slug_uppercase(self, board):
        board.slug = "123456ab"
        board.save()
        form_data = {
            "board_slug": " 12 34-56-AB",
        }
        form = BoardSearchForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data["board_slug"] == "123456ab"

    def test_search_boards_form_invalid(self):
        form_data = {
            "board_slug": "x",
        }
        form = BoardSearchForm(data=form_data)
        assert not form.is_valid()
        assert form.errors["board_slug"] == ["ID should be 6 or 8 letters and/or digits."]

    def test_search_boards_form_not_exist(self, board):
        test_slug = "123456ab" if board.slug != "123456ab" else "123456cd"
        form_data = {"board_slug": test_slug}
        form = BoardSearchForm(data=form_data)
        assert not form.is_valid()
        assert form.errors["board_slug"] == ["Board does not exist."]


class TestPostCreateForm:
    @pytest.mark.parametrize("is_additional_data_allowed", [True, False])
    @pytest.mark.parametrize("is_blank_data", [True, False])
    @pytest.mark.parametrize("data_type", ADDITIONAL_DATA_TYPE_CHOICES)
    @pytest.mark.parametrize("text", ["test content", None])
    def test_post_create_form_data_validation(
        self,
        is_additional_data_allowed,
        is_blank_data,
        json_string,
        data_type,
        text,
    ):
        form_data = {"content": text}
        json_data = None

        form = PostCreateForm(
            data=form_data,
            is_additional_data_allowed=is_additional_data_allowed,
            additional_data_type=data_type,
        )

        if is_additional_data_allowed and not is_blank_data and data_type in ["m", "c"]:
            json_data = json_string
            form.data["additional_data"] = json_data
            if "additional_data" not in form.changed_data:
                form.changed_data.append("additional_data")

        is_form_valid = form.is_valid()
        is_text_and_data_none = text is None and json_data is None
        if is_additional_data_allowed:
            if is_text_and_data_none:
                assert not is_form_valid
                if data_type == "c":
                    assert form.non_field_errors()[0] == "Content and molecule cannot be empty."
                else:
                    assert form.non_field_errors()[0] == "Content and additional data cannot be empty."
            else:
                assert is_form_valid
                if data_type in ["m", "c"] and not is_blank_data:
                    assert form.cleaned_data["additional_data"] == json.loads(json_data)
        elif text is None:
            assert not is_form_valid
            assert form.errors["content"] == ["This field is required."]
        else:
            assert is_form_valid

    def test_post_update_form_data_validation(self):
        pass
