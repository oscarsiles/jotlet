from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

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
        self.assertFalse(User.objects.filter(username=self.user.username).exists())

    def test_delete_staff(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("account_delete"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("account_delete"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("account_profile"))
        self.assertTrue(User.objects.filter(username=self.user2.username).exists())

    def test_delete_superuser(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("account_delete"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("account_delete"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("account_profile"))
        self.assertTrue(User.objects.filter(username=self.user3.username).exists())


class JotletLoginViewTest(TestCase):
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
