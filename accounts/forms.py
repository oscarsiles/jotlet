from allauth.account.forms import LoginForm, SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from crispy_bootstrap5.bootstrap5 import Field, FloatingField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout
from django import forms

from accounts.utils import hcaptcha_verified


def verify_hcaptcha(request):
    if not hcaptcha_verified(request):
        raise forms.ValidationError("Captcha challenge failed. Please try again.")


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["login"].label = "Username or e-mail"

        self.helper = FormHelper()
        self.helper.form_tag = False

        self.helper.layout = Layout(
            FloatingField("login"),
            FloatingField("password"),
        )

    def clean(self):
        verify_hcaptcha(self.request)
        return super().clean()

    def user_credentials(self):
        credentials = super().user_credentials()
        # Add Axes compatibility
        credentials["login"] = credentials.get("email") or credentials.get("username")
        return credentials


class CustomSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        self.fields["first_name"] = forms.CharField(
            max_length=150,
            label="First name",
        )
        self.fields["last_name"] = forms.CharField(
            max_length=150,
            label="Last name",
        )
        self.fields["optin_newsletter"] = forms.BooleanField(
            required=False,
            initial=False,
            label="Opt-in to newsletter",
        )

        self.helper = FormHelper(self)
        self.helper.form_tag = False

        self.helper.layout = Layout(
            Div(
                FloatingField("first_name", wrapper_class="flex-fill"),
                FloatingField("last_name", wrapper_class="flex-fill"),
                css_class="d-sm-flex justify-content-between gap-3",
            ),
            FloatingField("email"),
            FloatingField("username"),
            FloatingField("password1"),
            FloatingField("password2"),
            Field("optin_newsletter", wrapper_class="ms-2 form-check form-switch"),
        )

    def clean(self):
        verify_hcaptcha(self.request)
        return super().clean()


class CustomSocialSignupForm(SocialSignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["first_name"] = forms.CharField(
            max_length=150,
            initial=self.sociallogin.user.first_name,
            label="First name",
            disabled=True,
        )
        self.fields["last_name"] = forms.CharField(
            max_length=150,
            initial=self.sociallogin.user.last_name,
            label="Last name",
            disabled=True,
        )
        self.fields["email"] = forms.CharField(
            max_length=254,
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
        self.helper.form_tag = False

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
