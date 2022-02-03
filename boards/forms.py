
from django import forms
from django.core.validators import RegexValidator
slug_validator = RegexValidator("\d{6}$", "ID format needs to be ######.")

from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Fieldset, Layout, Submit
from crispy_forms.bootstrap import PrependedText


class SearchBoardsForm(forms.Form):
    board_slug = forms.CharField(label="Board ID", help_text="Enter the board ID given as ######", validators=[slug_validator])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False

        self.helper.layout = Layout(
            PrependedText('board_slug', 'Board ID', '<i class="fas fa-hashtag"></i>'),
            ButtonHolder(
                Submit('submit', 'Submit', css_class='button white')
            )
        )
