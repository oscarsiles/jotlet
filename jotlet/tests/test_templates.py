from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse


class JotletTestBaseGeneric(TestCase):
    def test_footer_feedback_no_email(self):
        response = self.client.get(reverse("boards:index"))
        self.assertNotContains(response, "Leave feedback")

    @override_settings(FEEDBACK_EMAIL="test@test.com")
    def test_footer_feedback_with_email(self):
        response = self.client.get(reverse("boards:index"))
        self.assertContains(
            response,
            f"mailto:{settings.FEEDBACK_EMAIL}?subject=Jotlet%20Feedback%20(v{settings.VERSION})",
        )
