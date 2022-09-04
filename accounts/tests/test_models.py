from django.test import TestCase

from .factories import UserFactory


class UserProfileTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user.profile.optin_newsletter = True
        cls.user.profile.save()

    def test_user_profile_string(self):
        self.assertEqual(str(self.user.profile), f"{self.user.username}'s profile")
