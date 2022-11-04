from cachalot.api import invalidate
from crispy_bootstrap5.bootstrap5 import FloatingField
from crispy_forms.bootstrap import Field, PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Div, Layout, Submit
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.urls import reverse

from .models import Board, BoardPreferences, Post

# make sure to support legacy 6-digit slugs
slug_validator = RegexValidator(r"^[a-z0-9]{8}$|^\d{6}$", "ID should be 6 or 8 lowercase letters and/or digits.")


def validate_board_exists(board_slug):
    try:
        Board.objects.get(slug=board_slug)
    except Board.DoesNotExist:
        raise forms.ValidationError("Board does not exist.")


def validate_percentage(percentage):
    if percentage < 0.0 or percentage > 1.0:
        raise forms.ValidationError("Value needs to be between 0.0 and 1.0.")


class BoardCreateForm(forms.ModelForm):
    class Meta:
        model = Board
        fields = ["title", "description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            FloatingField("title", placeholder="Title", autofocus=True),
            FloatingField("description", placeholder="Description"),
        )


class BoardFilterForm(forms.Form):
    board_list_type = "own"

    def __init__(self, *args, **kwargs):
        self.board_list_type = kwargs.pop("board_list_type", "own")
        super().__init__(*args, **kwargs)
        reverse_url = reverse("boards:board-list", kwargs={"board_list_type": self.board_list_type})

        if self.changed_data:
            self.fields[self.changed_data[0]].widget.attrs.update({"autofocus": "autofocus"})

        self.fields["after"].widget = forms.DateInput(attrs={"type": "date"})
        self.fields["before"].widget = forms.DateInput(attrs={"type": "date"})

        self.helper = FormHelper()
        self.helper.disable_csrf = True
        self.helper.form_show_labels = False
        self.helper.form_id = "board-filter-form"
        self.helper.attrs = {
            "hx-get": reverse_url,
            "hx-trigger": "filterChanged delay:500ms",
            "hx-target": "#board-list",
            "hx-swap": "innerHTML",
            "hx-indicator": ".htmx-indicator",
            "x-data": "boardFilter()",
        }

        self.helper.layout = Layout(
            Field(
                "q",
                placeholder="Search by title/description...",
                x_bind="keyup",
            ),
            Div(
                PrependedText(
                    "after",
                    "After",
                    wrapper_class="col-sm pe-sm-0",
                    onkeydown="return false",
                    x_bind="change",
                ),
                PrependedText(
                    "before",
                    "Before",
                    wrapper_class="col-sm ps-sm-0",
                    onkeydown="return false",
                    x_bind="change",
                ),
                css_class="row gap-sm-3",
            ),
        )

        if "owner" in self.fields:
            self.helper.layout.append(
                Field(
                    "owner",
                    placeholder="Search by username...",
                    x_bind="tagify",
                ),
            )


class BoardPreferencesForm(forms.ModelForm):
    checkbox_classes = "form-check-input h-auto my-0"
    initial_moderators = []
    initial_require_post_approval = False
    initial_board = None
    moderators = forms.CharField(
        label="Moderators",
        required=False,
    )

    class Meta:
        model = BoardPreferences
        exclude = ["board"]
        labels = {
            "type": "Board Type",
            "enable_latex": "Enable LaTeX",
            "require_post_approval": "Posts Require Approval",
            "allow_guest_replies": "Allow Guest Replies",
            "allow_image_uploads": "Allow Image Uploads",
        }

    def __init__(self, *args, **kwargs):
        self.initial_board = kwargs.pop("board")
        super().__init__(*args, **kwargs)

        self.fields["posting_allowed_from"].widget = forms.DateInput(
            format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
        )
        self.fields["posting_allowed_until"].widget = forms.DateInput(
            format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
        )

        self.initial_moderators = list(self.initial_board.preferences.moderators.all())
        self.initial["moderators"] = ",".join(map(lambda user: user.username, self.initial_moderators))
        self.initial_require_post_approval = self.initial["require_post_approval"]

        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_id = "board-preferences-form"
        webp_url = (
            self.instance.background_image.get_small_thumbnail_webp.url if self.instance.background_image else ""
        )
        jpeg_url = self.instance.background_image.get_small_thumbnail.url if self.instance.background_image else ""
        self.helper.attrs = {
            "hx-post": reverse("boards:board-preferences", kwargs={"slug": self.initial_board.slug}),
            "hx-target": "#modal-1-body-div",
            "hx-swap": "innerHTML",
            "x-data": "",
            "x-init": f"""$store.boardPreferences.type = '{self.initial["type"]}';
            $store.boardPreferences.bg_type = '{self.initial["background_type"]}';
            $store.boardPreferences.img_uuid = '{self.initial["background_image"]}';
            $store.boardPreferences.img_srcset_webp = '{webp_url}';
            $store.boardPreferences.img_srcset_jpeg = '{jpeg_url}';
            $store.boardPreferences.bg_opacity = '{self.initial["background_opacity"]}';""",
        }

        self.helper.layout = Layout(
            PrependedText(
                "posting_allowed_from",
                "Allow Posts From",
            ),
            PrependedText(
                "posting_allowed_until",
                "Allow Posts Until",
            ),
            PrependedText(
                "type",
                "Board Type",
                css_class="form-select h-auto my-0",
                x_model="$store.boardPreferences.type",
            ),
            Div(
                PrependedText(
                    "allow_guest_replies",
                    "Allow Guest Replies",
                    wrapper_class="d-flex",
                    css_class=self.checkbox_classes,
                ),
                x_show="$store.boardPreferences.type == 'r'",
            ),
            PrependedText(
                "background_type",
                "Background Type",
                css_class="form-select h-auto my-0",
                x_model="$store.boardPreferences.bg_type",
            ),
            Div(
                PrependedText(
                    "background_color",
                    "Background Color",
                    template="boards/components/forms/colorpicker.html",
                ),
                x_show="$store.boardPreferences.colorVisible",
            ),
            Div(
                PrependedText(
                    "background_image",
                    "Background Image",
                    template="boards/components/forms/imagepicker.html",
                ),
                PrependedText(
                    "background_opacity",
                    "Background Opacity",
                    template="boards/components/forms/opacitypicker.html",
                ),
                x_show="$store.boardPreferences.imageVisible",
            ),
            PrependedText(
                "enable_identicons",
                "Enable Identicons",
                wrapper_class="d-flex",
                css_class=self.checkbox_classes,
            ),
            PrependedText(
                "enable_latex",
                "Enable LaTeX",
                wrapper_class="d-flex",
                css_class=self.checkbox_classes,
            ),
            PrependedText(
                "allow_image_uploads",
                "Allow Images",
                wrapper_class="d-flex",
                css_class=self.checkbox_classes,
            ),
            PrependedText(
                "require_post_approval",
                "Require Approval",
                wrapper_class="d-flex",
                css_class=self.checkbox_classes,
            ),
            PrependedText(
                "reaction_type",
                "Reaction Type",
                css_class="form-select h-auto my-0",
            ),
            PrependedText(
                "moderators",
                "Moderators",
                placeholder="Add Moderators By Username",
                css_class="rounded-end",
            ),
            ButtonHolder(
                Submit(
                    "submit",
                    "Save Changes",
                    css_class="btn-success",
                    data_bs_dismiss="offcanvas",
                ),
                css_class="d-flex justify-content-end",
            ),
        )

    def clean_background_opacity(self):
        value = self.cleaned_data["background_opacity"]
        validate_percentage(value)
        return value

    def clean_moderators(self):
        moderators = self.cleaned_data["moderators"].split(",")
        value = []
        if len(moderators) > 0:
            user_model = get_user_model()
            for moderator in moderators:
                user = user_model.objects.filter(username=moderator).first()
                if user is not None:
                    value.append(user)

            if value != self.initial_moderators and settings.CACHALOT_ENABLED:
                invalidate(user_model)

        return value

    def clean_require_post_approval(self):
        value = self.cleaned_data["require_post_approval"]
        if "require_post_approval" in self.changed_data and not value:
            posts = Post.objects.filter(topic__board=self.initial_board)
            posts.invalidated_update(approved=True)

        return value


class SearchBoardsForm(forms.Form):
    board_slug = forms.CharField(
        label="Board ID",
        help_text="Enter the board ID given as #### #### (lowercase letters and/or digits only)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False

        self.helper.layout = Layout(
            PrependedText("board_slug", "Board ID", placeholder="#### ####", x_data="", x_mask="**** ****"),
            ButtonHolder(Submit("submit", "Submit")),
        )

    def clean_board_slug(self):
        board_slug = self.cleaned_data["board_slug"].replace(" ", "").replace("-", "")
        slug_validator(board_slug)
        validate_board_exists(board_slug)
        return board_slug.replace(" ", "")
