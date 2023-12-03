from http import HTTPStatus

import pytest
from allauth.core import context
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from pytest_lazy_fixtures import lf

from accounts.views import JotletLoginView
from jotlet.tests.utils import create_session

from .factories import USER_TEST_PASSWORD

HCAPTCHA_TEST_RESPONSE = "10000000-aaaa-bbbb-cccc-000000000001"


class TestJotletAccountDeleteView:
    @pytest.mark.parametrize(
        ("test_user", "expected_redirect", "expected_exists"),
        [
            (None, f"{reverse("account_login")}?next={reverse("account_delete")}", False),
            (lf("user"), reverse("boards:index"), False),
            (lf("user_staff"), reverse("account_profile"), True),
            (lf("user_superuser"), reverse("account_profile"), True),
        ],
    )
    def test_delete_user(self, client, test_user, expected_redirect, expected_exists):
        if test_user:
            client.login(username=test_user, password=USER_TEST_PASSWORD)
        response = client.get(reverse("account_delete"))
        assert response.status_code == HTTPStatus.OK if test_user else HTTPStatus.FOUND
        response = client.post(reverse("account_delete"))
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == expected_redirect
        assert get_user_model().objects.filter(username=test_user).exists() == expected_exists


class TestJotletLoginView:
    @pytest.mark.parametrize(
        ("hcaptcha_response", "success"),
        [(HCAPTCHA_TEST_RESPONSE, True), ("incorrect_captcha_response", False)],
    )
    def test_hcaptcha(self, settings, client, user, hcaptcha_response, success):
        settings.HCAPTCHA_ENABLED = True
        settings.CF_TURNSTILE_ENABLED = False

        response = client.post(
            reverse("account_login"),
            {
                "login": user.username,
                "password": USER_TEST_PASSWORD,
                "h-captcha-response": hcaptcha_response,
            },
        )
        assert response.status_code == HTTPStatus.OK
        if success:
            assert response.headers["HX-Redirect"] == reverse(settings.LOGIN_REDIRECT_URL)
        else:
            assert (
                response.context_data["form"].errors.get("__all__")[0]
                == "Captcha challenge failed. Please try again."
            )

    def test_successful_cf_turnstile_login(self, settings, client, user):
        settings.HCAPTCHA_ENABLED = False
        settings.CF_TURNSTILE_ENABLED = True

        response = client.post(
            reverse("account_login"),
            {
                "login": user.username,
                "password": USER_TEST_PASSWORD,
                "cf-turnstile-response": "test",
            },
        )
        assert response.status_code == HTTPStatus.OK
        assert response.headers["HX-Redirect"] == reverse(settings.LOGIN_REDIRECT_URL)

    def test_cf_turnstile_fail(self, settings, client, user):
        settings.CF_TURNSTILE_ENABLED = True
        settings.HCAPTCHA_ENABLED = False
        settings.CF_TURNSTILE_SITE_KEY = "2x00000000000000000000AB"  # always blocks
        settings.CF_TURNSTILE_SECRET_KEY = "2x0000000000000000000000000000000AA"  # always fails  # noqa: S105

        response = client.post(
            reverse("account_login"),
            {
                "login": user.username,
                "password": USER_TEST_PASSWORD,
                "cf-turnstile-response": "test",
            },
        )
        assert response.status_code == HTTPStatus.OK
        assert response.context_data["form"].errors.get("__all__")[0] == "Captcha challenge failed. Please try again."

    def test_incorrect_login(self, client):
        response = client.post(
            reverse("account_login"),
            {
                "login": "incorrect_login",
                "password": "incorrect_password",
                "h-captcha-response": HCAPTCHA_TEST_RESPONSE,
            },
        )
        assert response.status_code == HTTPStatus.OK
        assert response.context_data["form"].errors is not None

    def test_remember_me(self, settings, rf, user):
        settings.HCAPTCHA_ENABLED = False
        settings.MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"

        request = rf.post(
            reverse("account_login"),
            {
                "login": user.username,
                "password": USER_TEST_PASSWORD,
                "h-captcha-response": HCAPTCHA_TEST_RESPONSE,
                "remember_me": True,
            },
        )
        request.user = AnonymousUser()
        request._messages = messages.storage.default_storage(request)
        create_session(request)
        with context.request_context(request):
            response = JotletLoginView.as_view()(request)
        assert response.status_code == HTTPStatus.OK
        assert not request.session.get_expire_at_browser_close()

    def test_not_remember_me(self, settings, rf, user):
        settings.HCAPTCHA_ENABLED = False
        settings.MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"

        from django.contrib import messages

        request = rf.post(
            reverse("account_login"),
            {
                "login": user.username,
                "password": USER_TEST_PASSWORD,
                "h-captcha-response": HCAPTCHA_TEST_RESPONSE,
                "remember_me": False,
            },
        )
        request.user = AnonymousUser()
        request._messages = messages.storage.default_storage(request)
        create_session(request)
        with context.request_context(request):
            response = JotletLoginView.as_view()(request)
        assert response.status_code == HTTPStatus.OK
        assert request.session.get_expire_at_browser_close()


class TestJotletProfileView:
    def test_profile_anonymous(self, client):
        response = client.get(reverse("account_profile"))
        assert response.status_code == HTTPStatus.FOUND

    def test_profile_user(self, client, user):
        client.login(username=user.username, password=USER_TEST_PASSWORD)
        response = client.get(reverse("account_profile"))
        assert response.status_code == HTTPStatus.OK


class TestJotletProfileEditView:
    @pytest.mark.parametrize("optin_newsletter", [True, False])
    def test_toggle_optin_newsletter(self, client, user, optin_newsletter):
        client.login(username=user.username, password=USER_TEST_PASSWORD)
        if optin_newsletter:
            assert user.profile.optin_newsletter is not optin_newsletter

        response = client.post(
            reverse("account_profile_edit"),
            {"optin_newsletter": optin_newsletter},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse("account_profile")
        user.refresh_from_db()
        assert user.profile.optin_newsletter is optin_newsletter
