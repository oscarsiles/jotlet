from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

HCAPTCHA_TEST_RESPONSE = "10000000-aaaa-bbbb-cccc-000000000001"


class JotletLoginViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(username="test_user", password="test_password")

    def test_successful_login(self):
        response = self.client.post(
            reverse("account_login"),
            {"login": "test_user", "password": "test_password", "h-captcha-response": HCAPTCHA_TEST_RESPONSE},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["HX-Redirect"], reverse(settings.LOGIN_REDIRECT_URL))

    def test_incorrect_login(self):
        response = self.client.post(
            reverse("account_login"),
            {"login": "incorrect_login", "password": "test_password", "h-captcha-response": HCAPTCHA_TEST_RESPONSE},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context_data["form"].error_messages.get("username_password_mismatch"))
