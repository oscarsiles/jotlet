import pytest
from django.urls import reverse


class TestJotletBaseGeneric:
    class TestJotletBaseGeneric:
        @pytest.mark.parametrize(("umami_script_url", "umami_website_id"), [("", ""), ("https://test.com", "12345")])
        def test_head_umami(self, settings, client, umami_script_url, umami_website_id):
            is_umami = bool(umami_script_url) and bool(umami_website_id)

            settings.UMAMI_SCRIPT_URL = umami_script_url
            settings.UMAMI_WEBSITE_ID = umami_website_id
            settings.UMAMI_ENABLED = is_umami

            response = client.get(reverse("boards:index"))
            assert (f'src="{settings.UMAMI_SCRIPT_URL}"' in response.content.decode("utf-8")) == is_umami
            assert (f'data-website-id="{settings.UMAMI_WEBSITE_ID}"' in response.content.decode("utf-8")) == is_umami

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
