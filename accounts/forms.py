from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from crispy_bootstrap5.bootstrap5 import Field, FloatingField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout
from django import forms


class CustomSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["first_name"] = forms.CharField(
            max_length=30,
            label="First name",
        )
        self.fields["last_name"] = forms.CharField(
            max_length=30,
            label="Last name",
        )
        self.fields["optin_newsletter"] = forms.BooleanField(
            required=False,
            initial=False,
            label="Opt-in to newsletter",
        )

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
            Field("optin_newsletter", wrapper_class="ms-2 form-check form-switch"),
        )


class CustomSocialSignupForm(SocialSignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["first_name"] = forms.CharField(
            max_length=30,
            initial=self.sociallogin.user.first_name,
            label="First name",
            disabled=True,
        )
        self.fields["last_name"] = forms.CharField(
            max_length=30,
            initial=self.sociallogin.user.last_name,
            label="Last name",
            disabled=True,
        )
        self.fields["email"] = forms.CharField(
            max_length=30,
            initial=self.initial.get("email"),
            label="E-mail",
            disabled=True,
        )
        self.fields["optin_newsletter"] = forms.BooleanField(
            required=False,
            initial=False,
            label="Opt-in to newsletter",
        )

        self.helper = FormHelper(self)

        self.helper.layout = Layout(
            Div(
                FloatingField("first_name", wrapper_class="flex-fill"),
                FloatingField("last_name", wrapper_class="flex-fill"),
                css_class="d-sm-flex justify-content-between gap-3",
            ),
            FloatingField("email", disabled=""),
            FloatingField("username"),
            Field("optin_newsletter", wrapper_class="ms-2 form-check form-switch"),
        )
