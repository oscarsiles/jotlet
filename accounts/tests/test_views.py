from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse

from accounts.views import JotletLoginView
from boards.tests.utils import create_session

from .factories import USER_TEST_PASSWORD, UserFactory

HCAPTCHA_TEST_RESPONSE = "10000000-aaaa-bbbb-cccc-000000000001"


class JotletDeleteViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory(is_staff=True)
        cls.user3 = UserFactory(is_staff=True, is_superuser=True)

    def test_delete_anonymous(self):
        response = self.client.get(reverse("account_delete"))
        self.assertEqual(response.status_code, 302)

    def test_delete_user(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("account_delete"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("account_delete"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("boards:index"))
        self.assertFalse(get_user_model().objects.filter(username=self.user.username).exists())

    def test_delete_staff(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("account_delete"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("account_delete"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("account_profile"))
        self.assertTrue(get_user_model().objects.filter(username=self.user2.username).exists())

    def test_delete_superuser(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("account_delete"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("account_delete"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("account_profile"))
        self.assertTrue(get_user_model().objects.filter(username=self.user3.username).exists())


class JotletLoginViewTest(TestCase):
    @classmethod
    def setUp(cls):
        cls.factory = RequestFactory()

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_successful_hcaptcha_login(self):
        response = self.client.post(
            reverse("account_login"),
            {
                "login": self.user.username,
                "password": USER_TEST_PASSWORD,
                "h-captcha-response": HCAPTCHA_TEST_RESPONSE,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["HX-Redirect"], reverse(settings.LOGIN_REDIRECT_URL))

    @override_settings(
        HCAPTCHA_ENABLED=False,
        CF_TURNSTILE_ENABLED=True,
    )
    def test_successful_cf_turnstile_login(self):
        response = self.client.post(
            reverse("account_login"),
            {
                "login": self.user.username,
                "password": USER_TEST_PASSWORD,
                "cf-turnstile-response": "test",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["HX-Redirect"], reverse(settings.LOGIN_REDIRECT_URL))

    def test_hcaptcha_fail(self):
        response = self.client.post(
            reverse("account_login"),
            {
                "login": self.user.username,
                "password": USER_TEST_PASSWORD,
                "h-captcha-response": "incorrect_captcha_response",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context_data["form"].errors.get("__all__")[0], "Captcha challenge failed. Please try again."
        )

    @override_settings(
        HCAPTCHA_ENABLED=False,
        CF_TURNSTILE_ENABLED=True,
        CF_TURNSTILE_SITE_KEY="2x00000000000000000000AB",  # blocks all challenges
        CF_TURNSTILE_SECRET_KEY="2x0000000000000000000000000000000AA",
    )
    def test_cf_turnstile_fail(self):
        response = self.client.post(
            reverse("account_login"),
            {
                "login": self.user.username,
                "password": USER_TEST_PASSWORD,
                "cf-turnstile-response": "test",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context_data["form"].errors.get("__all__")[0], "Captcha challenge failed. Please try again."
        )

    def test_incorrect_login(self):
        response = self.client.post(
            reverse("account_login"),
            {
                "login": "incorrect_login",
                "password": "incorrect_password",
                "h-captcha-response": HCAPTCHA_TEST_RESPONSE,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context_data["form"].errors)

    @override_settings(
        HCAPTCHA_ENABLED=False,
        MESSAGE_STORAGE="django.contrib.messages.storage.cookie.CookieStorage",
    )
    def test_remember_me(self):
        from django.contrib import messages

        request = self.factory.post(
            reverse("account_login"),
            {
                "login": self.user.username,
                "password": USER_TEST_PASSWORD,
                "h-captcha-response": HCAPTCHA_TEST_RESPONSE,
                "remember_me": True,
            },
        )
        request.user = AnonymousUser()
        request._messages = messages.storage.default_storage(request)
        create_session(request)
        response = JotletLoginView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(request.session.get_expire_at_browser_close())

    @override_settings(
        HCAPTCHA_ENABLED=False,
        MESSAGE_STORAGE="django.contrib.messages.storage.cookie.CookieStorage",
    )
    def test_not_remember_me(self):
        from django.contrib import messages

        request = self.factory.post(
            reverse("account_login"),
            {
                "login": self.user.username,
                "password": USER_TEST_PASSWORD,
                "h-captcha-response": HCAPTCHA_TEST_RESPONSE,
                "remember_me": False,
            },
        )
        request.user = AnonymousUser()
        request._messages = messages.storage.default_storage(request)
        create_session(request)
        response = JotletLoginView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(request.session.get_expire_at_browser_close())


class JotletProfileViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_profile_anonymous(self):
        response = self.client.get(reverse("account_profile"))
        self.assertEqual(response.status_code, 302)

    def test_profile_user(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("account_profile"))
        self.assertEqual(response.status_code, 200)

    def test_link_header(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("account_profile"))
        link_header = response.get("Link")
        self.assertIsNotNone(link_header)

        self.assertIn(f"<{static('css/3rdparty/bootstrap-5.2.2.min.css')}>; rel=preload; as=style", link_header)
        self.assertIn(f"<{static('accounts/js/profile.js')}>; rel=preload; as=script", link_header)
