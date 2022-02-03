from django import forms
from django.core.validators import RegexValidator
slug_validator = RegexValidator("\d{6}$", "ID format needs to be ######.")

from .models import Board

from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Layout, Submit
from crispy_forms.bootstrap import PrependedText

def validate_board_exists(board_slug):
    try:
        Board.objects.get(slug=board_slug)
    except Board.DoesNotExist:
        raise forms.ValidationError("Board does not exist.")

class SearchBoardsForm(forms.Form):
    board_slug = forms.CharField(label="Board ID", help_text="Enter the board ID given as ######")

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
    
    def clean_board_slug(self):
        board_slug = self.cleaned_data['board_slug'].replace(' ', '').replace('-', '')
        slug_validator(board_slug)
        validate_board_exists(board_slug)
        return board_slug.replace(' ', '')
