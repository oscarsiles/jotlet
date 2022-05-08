from django.contrib.auth.models import User
from django.test import TestCase


class UserProfileTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user(username="test_user", password="test_password")
        user.profile.optin_newsletter = True
        user.profile.save()

    def test_user_profile_string(self):
        user = User.objects.get(username="test_user")
        self.assertEqual(str(user.profile), f"{user.username}'s profile")
