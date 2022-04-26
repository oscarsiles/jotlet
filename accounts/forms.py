from allauth.account.forms import SignupForm
from crispy_bootstrap5.bootstrap5 import FloatingField
from crispy_forms.bootstrap import Field, InlineRadios, PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Div, Layout, Submit
from django import forms


class CustomSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["first_name"] = forms.CharField(max_length=30, label="First name")
        self.fields["last_name"] = forms.CharField(max_length=30, label="Last name")

        self.helper = FormHelper(self)

        self.helper.layout = Layout(
            Div(
                FloatingField("first_name"),
                FloatingField("last_name"),
                css_class="d-sm-flex gap-3",
            ),
            FloatingField("email"),
            FloatingField("username"),
            FloatingField("password1"),
            FloatingField("password2"),
        )
