from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.templatetags.static import static
from django.test import override_settings
from django.urls import reverse

from accounts.views import JotletLoginView
from jotlet.tests.utils import create_session

from .factories import USER_TEST_PASSWORD

HCAPTCHA_TEST_RESPONSE = "10000000-aaaa-bbbb-cccc-000000000001"


class TestJotletAccountDeleteView:
    def test_delete_anonymous(self, client):
        response = client.get(reverse("account_delete"))
        assert response.status_code == 302

    def test_delete_user(self, client, user):
        client.login(username=user.username, password=USER_TEST_PASSWORD)
        response = client.get(reverse("account_delete"))
        assert response.status_code == 200
        response = client.post(reverse("account_delete"))
        assert response.status_code == 302
        assert response.url == reverse("boards:index")
        assert not get_user_model().objects.filter(username=user.username).exists()

    def test_delete_staff(self, client, user_staff):
        client.login(username=user_staff.username, password=USER_TEST_PASSWORD)
        response = client.get(reverse("account_delete"))
        assert response.status_code == 200
        response = client.post(reverse("account_delete"))
        assert response.status_code == 302
        assert response.url == reverse("account_profile")
        assert get_user_model().objects.filter(username=user_staff.username).exists()

    def test_delete_superuser(self, client, user_superuser):
        client.login(username=user_superuser.username, password=USER_TEST_PASSWORD)
        response = client.get(reverse("account_delete"))
        assert response.status_code == 200
        response = client.post(reverse("account_delete"))
        assert response.status_code == 302
        assert response.url == reverse("account_profile")
        assert get_user_model().objects.filter(username=user_superuser.username).exists()


class TestJotletLoginView:
    def test_successful_hcaptcha_login(self, client, user):
        response = client.post(
            reverse("account_login"),
            {
                "login": user.username,
                "password": USER_TEST_PASSWORD,
                "h-captcha-response": HCAPTCHA_TEST_RESPONSE,
            },
        )
        assert response.status_code == 200
        assert response.headers["HX-Redirect"] == reverse(settings.LOGIN_REDIRECT_URL)

    @override_settings(
        HCAPTCHA_ENABLED=False,
        CF_TURNSTILE_ENABLED=True,
    )
    def test_successful_cf_turnstile_login(self, client, user):
        response = client.post(
            reverse("account_login"),
            {
                "login": user.username,
                "password": USER_TEST_PASSWORD,
                "cf-turnstile-response": "test",
            },
        )
        assert response.status_code == 200
        assert response.headers["HX-Redirect"] == reverse(settings.LOGIN_REDIRECT_URL)

    def test_hcaptcha_fail(self, client, user):
        response = client.post(
            reverse("account_login"),
            {
                "login": user.username,
                "password": USER_TEST_PASSWORD,
                "h-captcha-response": "incorrect_captcha_response",
            },
        )
        assert response.status_code == 200
        assert response.context_data["form"].errors.get("__all__")[0] == "Captcha challenge failed. Please try again."

    @override_settings(
        HCAPTCHA_ENABLED=False,
        CF_TURNSTILE_ENABLED=True,
        CF_TURNSTILE_SITE_KEY="2x00000000000000000000AB",  # blocks all challenges
        CF_TURNSTILE_SECRET_KEY="2x0000000000000000000000000000000AA",
    )
    def test_cf_turnstile_fail(self, client, user):
        response = client.post(
            reverse("account_login"),
            {
                "login": user.username,
                "password": USER_TEST_PASSWORD,
                "cf-turnstile-response": "test",
            },
        )
        assert response.status_code == 200
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
        assert response.status_code == 200
        assert response.context_data["form"].errors is not None

    @override_settings(
        HCAPTCHA_ENABLED=False,
        MESSAGE_STORAGE="django.contrib.messages.storage.cookie.CookieStorage",
    )
    def test_remember_me(self, rf, user):
        from django.contrib import messages

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
        response = JotletLoginView.as_view()(request)
        assert response.status_code == 200
        assert not request.session.get_expire_at_browser_close()

    @override_settings(
        HCAPTCHA_ENABLED=False,
        MESSAGE_STORAGE="django.contrib.messages.storage.cookie.CookieStorage",
    )
    def test_not_remember_me(self, rf, user):
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
        response = JotletLoginView.as_view()(request)
        assert response.status_code == 200
        assert request.session.get_expire_at_browser_close()


class TestJotletProfileView:
    def test_profile_anonymous(self, client):
        response = client.get(reverse("account_profile"))
        assert response.status_code == 302

    def test_profile_user(self, client, user):
        client.login(username=user.username, password=USER_TEST_PASSWORD)
        response = client.get(reverse("account_profile"))
        assert response.status_code == 200

    def test_link_header(self, client, user):
        client.login(username=user.username, password=USER_TEST_PASSWORD)
        response = client.get(reverse("account_profile"))
        link_header = response.get("Link")
        assert link_header is not None

        assert f"<{static('css/vendor/bootstrap-5.3.0-alpha1.min.css')}>; rel=preload; as=style" in link_header
        assert f"<{static('accounts/js/profile.js')}>; rel=preload; as=script" in link_header


class TestJotletProfileEditView:
    def test_toggle_optin_newsletter(self, client, user):
        client.login(username=user.username, password=USER_TEST_PASSWORD)
        assert user.profile.optin_newsletter is False

        response = client.post(
            reverse("account_profile_edit"),
            {"optin_newsletter": True},
        )
        assert response.status_code == 302
        assert response.url == reverse("account_profile")
        user.refresh_from_db()
        assert user.profile.optin_newsletter is True

        response = client.post(
            reverse("account_profile_edit"),
            {"optin_newsletter": False},
        )
        assert response.status_code == 302
        assert response.url == reverse("account_profile")
        user.refresh_from_db()
        assert user.profile.optin_newsletter is False
