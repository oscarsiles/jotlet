from ast import Raise

from django import forms
from django.core.validators import RegexValidator
from django.urls import reverse

slug_validator = RegexValidator("\d{6}$", "ID format needs to be ######.")

from crispy_forms.bootstrap import Field, InlineRadios, PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Div, Layout, Submit
from django.contrib.auth.models import User
from tagify.fields import TagField

from .models import BACKGROUND_TYPE, Board, BoardPreferences


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
        super(BoardFilterForm, self).__init__(*args, **kwargs)
        reverse_url = reverse("boards:board-list")

        owner_list = []
        try:
            list = self.data["owner"].split(",")
            for user in list:
                owner_list.append(user)
            self.data["owner"] = owner_list
        except Exception as e:
            Raise(e)

        if self.changed_data:
            self.fields[self.changed_data[0]].widget.attrs.update({"autofocus": "autofocus"})

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
        }

        self.helper.layout = Layout(
            Field(
                "q",
                placeholder="Search by topic/subject...",
            ),
        )

        if "created_at" in self.fields:
            self.fields["created_at__lt"].widget = forms.DateInput(attrs={"type": "date"})
            self.fields["created_at__gt"].widget = forms.DateInput(attrs={"type": "date"})
            self.helper.layout.append(
                Div(
                    PrependedText("created_at__gt", "After", wrapper_class="col-sm", onkeydown="return false"),
                    PrependedText("created_at__lt", "Before", wrapper_class="col-sm", onkeydown="return false"),
                    css_class="row",
                ),
            )

        if "owner" in self.fields:
            self.helper.layout.append(
                Field(
                    "owner",
                    placeholder="Search by username...",
                ),
            )


class BoardPreferencesForm(forms.ModelForm):
    moderators = TagField(
        label="Moderators",
        required=False,
        place_holder="Add Moderators By Username",
        delimiters=" ",
    )

    class Meta:
        model = BoardPreferences
        exclude = ["board"]
        labels = {
            "enable_latex": "Enable LaTeX",
            "require_approval": "Posts Require Approval",
        }

    def __init__(self, *args, **kwargs):
        self.slug = kwargs.pop("slug")
        super().__init__(*args, **kwargs)

        moderator_list = []
        for user in self.instance.moderators.all():
            moderator_list.append(user.username)
        self.initial["moderators"] = moderator_list

        self.fields["background_type"] = forms.ChoiceField(
            choices=BACKGROUND_TYPE,
            widget=forms.RadioSelect,
            label=False,
        )
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_id = "board-preferences-form"
        self.helper.attrs = {
            "hx-post": reverse("boards:board-preferences", kwargs={"slug": self.slug}),
            "hx-target": "#modal-1-body-div",
            "hx-swap": "innerHTML",
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
                            css_class="",
                        ),
                        css_class="input-group",
                    ),
                ),
                css_class="mb-3",
            ),
            PrependedText(
                "background_color",
                "Background Color",
                template="boards/components/forms/colorpicker.html",
            ),
            PrependedText(
                "background_image",
                "Background Image",
                template="boards/components/forms/imagepicker.html",
            ),
            PrependedText(
                "background_opacity",
                "Background Opacity",
                placeholder="Background Image Opacity",
                min=0.0,
                max=1.0,
                step=0.1,
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
            PrependedText(
                "moderators",
                "Moderators",
            ),
            ButtonHolder(
                Submit("submit", "Save", hidden="true")
            ),  # Hidden submit button, use modal one to trigger form submit
        )

    def clean_background_opacity(self):
        value = self.cleaned_data["background_opacity"]
        validate_percentage(value)
        return value

    def clean_background_image(self):
        value = self.cleaned_data["background_image"]
        if value == None:
            value == ""
        return value

    def clean_moderators(self):
        moderators = self.cleaned_data["moderators"]
        value = []
        for moderator in moderators:
            try:
                user = User.objects.get(username=moderator)
                value.append(user)
            except User.DoesNotExist:
                pass
        return value


class SearchBoardsForm(forms.Form):
    board_slug = forms.CharField(label="Board ID", help_text="Enter the board ID given as ######")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False

        self.helper.layout = Layout(
            PrependedText("board_slug", "Board ID", '<i class="fas fa-hashtag"></i>'),
            ButtonHolder(Submit("submit", "Submit", css_class="button white")),
        )

    def clean_board_slug(self):
        board_slug = self.cleaned_data["board_slug"].replace(" ", "").replace("-", "")
        slug_validator(board_slug)
        validate_board_exists(board_slug)
        return board_slug.replace(" ", "")
