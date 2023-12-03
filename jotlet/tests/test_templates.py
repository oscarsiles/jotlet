from django.urls import reverse


class TestJotletBaseGeneric:
    def test_footer_feedback_no_email(self, client):
        response = client.get(reverse("boards:index"))
        assert "Leave feedback" not in response.content.decode("utf-8")

    def test_footer_feedback_with_email(self, settings, client):
        settings.FEEDBACK_EMAIL = "test@test.com"

        response = client.get(reverse("boards:index"))
        assert (
            f"mailto:{settings.FEEDBACK_EMAIL}?subject=Jotlet%20Feedback%20(v{settings.VERSION})"
            in response.content.decode("utf-8")
        )
