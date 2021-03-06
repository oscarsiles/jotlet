from cachalot.api import invalidate
from crispy_forms.bootstrap import Field, InlineRadios, PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Div, Layout, Submit
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.urls import reverse

from .models import BACKGROUND_TYPE, REACTION_TYPE, Board, BoardPreferences, Post

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


class BoardFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reverse_url = reverse("boards:board-list")

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
    initial_moderators = []
    initial_require_approval = False
    initial_board = None
    moderators = forms.CharField(
        label="Moderators",
        required=False,
    )

    class Meta:
        model = BoardPreferences
        exclude = ["board"]
        labels = {
            "enable_latex": "Enable LaTeX",
            "require_approval": "Posts Require Approval",
        }

    def __init__(self, *args, **kwargs):
        self.initial_board = kwargs.pop("board")
        super().__init__(*args, **kwargs)

        self.initial_moderators = list(self.initial_board.preferences.moderators.all())
        self.initial["moderators"] = ",".join(map(lambda user: user.username, self.initial_moderators))
        self.initial_require_approval = self.initial["require_approval"]

        self.fields["background_type"] = forms.ChoiceField(
            choices=BACKGROUND_TYPE,
            widget=forms.RadioSelect,
            label=False,
        )
        self.fields["reaction_type"] = forms.ChoiceField(
            choices=REACTION_TYPE,
            widget=forms.RadioSelect,
            label=False,
        )

        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_id = "board-preferences-form"
        webp_url = self.instance.background_image.get_thumbnail_webp.url if self.instance.background_image else ""
        jpeg_url = self.instance.background_image.get_thumbnail.url if self.instance.background_image else ""
        self.helper.attrs = {
            "hx-post": reverse("boards:board-preferences", kwargs={"slug": self.initial_board.slug}),
            "hx-target": "#modal-1-body-div",
            "hx-swap": "innerHTML",
            "x-data": "",
            "x-init": f"""$store.boardPreferences.bg_type = '{self.initial["background_type"]}';
            $store.boardPreferences.img_uuid = '{self.initial["background_image"]}';
            $store.boardPreferences.img_srcset_webp = '{webp_url}';
            $store.boardPreferences.img_srcset_jpeg = '{jpeg_url}';
            $store.boardPreferences.bg_opacity = '{self.initial["background_opacity"]}';""",
        }

        self.helper.layout = Layout(
            Div(  # Div for background type (blame Bootstrap + crispy forms)
                Div(
                    Div(
                        HTML('<span class="input-group-text">Background Type</span>'),
                        InlineRadios(
                            "background_type",
                            wrapper_class="form-control",
                            id="id_background_type",
                            css_class="d-flex justify-content-around",
                            x_model="$store.boardPreferences.bg_type",
                            x_init="() => { $el.parentElement.classList.remove('mb-3') }",
                        ),
                        css_class="input-group",
                    ),
                ),
                css_class="mb-3",
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
                "enable_latex",
                "Enable LaTeX",
                wrapper_class="d-flex flex-row",
                css_class="form-check-input my-0",
                style="height: auto;",
            ),
            PrependedText(
                "require_approval",
                "Posts Require Approval",
                wrapper_class="d-flex flex-row",
                css_class="form-check-input my-0",
                style="height: auto;",
            ),
            Div(  # Div for reaction type (blame Bootstrap + crispy forms)
                Div(
                    Div(
                        HTML('<span class="input-group-text">Reaction Type</span>'),
                        InlineRadios(
                            "reaction_type",
                            wrapper_class="form-control",
                            id="id_reaction_type",
                            css_class="d-flex justify-content-around",
                            x_init="() => { $el.parentElement.classList.remove('mb-3') }",
                        ),
                        css_class="input-group",
                    ),
                ),
                css_class="mb-3",
            ),
            PrependedText(
                "moderators",
                "Moderators",
                placeholder="Add Moderators By Username",
            ),
            ButtonHolder(
                Submit("submit", "Save", hidden="true")
            ),  # Hidden submit button, use modal one to trigger form submit
        )

    def clean_background_opacity(self):
        value = self.cleaned_data["background_opacity"]
        validate_percentage(value)
        return value

    def clean_moderators(self):
        moderators = self.cleaned_data["moderators"].split(",")
        value = []
        for moderator in moderators:
            if User.objects.filter(username=moderator).exists():
                user = User.objects.get(username=moderator)
                value.append(user)

        if value != self.initial_moderators and settings.CACHALOT_ENABLED:
            invalidate(User)

        return value

    def clean_require_approval(self):
        value = self.cleaned_data["require_approval"]
        if "require_approval" in self.changed_data and not value:
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
