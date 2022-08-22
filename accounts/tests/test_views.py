from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

HCAPTCHA_TEST_RESPONSE = "10000000-aaaa-bbbb-cccc-000000000001"


class JotletDeleteViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(username="test", password="test")
        User.objects.create_user(username="test2", password="test2", is_staff=True)
        User.objects.create_superuser(username="test3", password="test3")

    def test_delete_anonymous(self):
        response = self.client.get(reverse("account_delete"))
        self.assertEqual(response.status_code, 302)

    def test_delete_user(self):
        self.client.login(username="test", password="test")
        response = self.client.get(reverse("account_delete"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("account_delete"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("boards:index"))
        self.assertFalse(User.objects.filter(username="test").exists())

    def test_delete_staff(self):
        self.client.login(username="test2", password="test2")
        response = self.client.get(reverse("account_delete"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("account_delete"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("account_profile"))
        self.assertTrue(User.objects.filter(username="test2").exists())

    def test_delete_superuser(self):
        self.client.login(username="test3", password="test3")
        response = self.client.get(reverse("account_delete"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("account_delete"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("account_profile"))
        self.assertTrue(User.objects.filter(username="test3").exists())


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

    def test_hcaptcha_fail(self):
        response = self.client.post(
            reverse("account_login"),
            {"login": "test_user", "password": "test_password", "h-captcha-response": "incorrect_captcha_response"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context_data["form"].errors.get("__all__")[0], "Captcha challenge failed. Please try again."
        )

    def test_incorrect_login(self):
        response = self.client.post(
            reverse("account_login"),
            {"login": "incorrect_login", "password": "test_password", "h-captcha-response": HCAPTCHA_TEST_RESPONSE},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context_data["form"].errors)
