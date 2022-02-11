from django import forms
from django.core.validators import RegexValidator
from django.urls import reverse
slug_validator = RegexValidator("\d{6}$", "ID format needs to be ######.")

from .models import Board, BACKGROUND_TYPE, BoardPreferences

from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Layout, Submit
from crispy_forms.bootstrap import Field, PrependedText

def validate_board_exists(board_slug):
    try:
        Board.objects.get(slug=board_slug)
    except Board.DoesNotExist:
        raise forms.ValidationError("Board does not exist.")

def validate_percentage(percentage):
    if percentage < 0.0 or percentage > 1.0:
        raise forms.ValidationError("Value needs to be between 0.0 and 1.0.")

class BoardPreferencesForm(forms.ModelForm):
    class Meta:
        model = BoardPreferences
        exclude = ['board']
        labels = {
            'enable_latex': 'Enable LaTeX',
        }

    def __init__(self, *args, **kwargs):
        self.slug = kwargs.pop('slug')
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.attrs = {
            'hx-post': reverse('boards:board-preferences', kwargs={'slug': self.slug}),
            'hx-swap': 'this',
            }

        self.helper.layout = Layout(
            PrependedText('background_type', 'Background Type', placeholder='Background Type'),
            PrependedText('background_color', 'Background Color', template='boards/components/forms/colorpicker.html'),
            PrependedText('background_image', 'Background Image', placeholder='Background Image'),
            PrependedText('background_opacity', 'Background Opacity', placeholder='Background Image Opacity'),
            PrependedText('enable_latex', 'Enable LaTeX', wrapper_class='d-flex flex-row', css_class='form-check-input my-0', style='height: auto;'),
            PrependedText('require_approval', 'Posts Require Approval', wrapper_class='d-flex flex-row', css_class='form-check-input my-0', style='height: auto;'),
            ButtonHolder(
                Submit('submit', 'Save', css_class='btn btn-success')
            )
        )
    
    def clean_background_opacity(self):
        value = self.cleaned_data['background_opacity']
        validate_percentage(value)
        return value


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
