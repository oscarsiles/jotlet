from django.templatetags.static import static
from django.urls import reverse


class TestBoardListLinkHeaderMixin:
    def test_dispatch_anonymous(self, client):
        response = client.get(reverse("boards:index"))
        link_header = response.get("Link")
        assert response.status_code == 200
        assert link_header is not None

        assert f"<{static('boards/js/index.js')}>; rel=preload; as=script" in link_header
        assert static("boards/js/components/board_list.js") not in link_header
        assert static("vendor/tagify-4.17.8/tagify.min.css") not in link_header
        assert static("vendor/tagify-4.17.8/tagify.min.js") not in link_header

    def test_dispatch_authenticated(self, client, user):
        client.force_login(user)

        response = client.get(reverse("boards:index"))
        link_header = response.get("Link")
        assert response.status_code == 200
        assert link_header is not None

        assert f"<{static('boards/js/index.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('boards/js/components/board_list.js')}>; rel=preload; as=script" in link_header
        assert static("vendor/tagify-4.17.8/tagify.min.css") not in link_header
        assert static("vendor/tagify-4.17.8/tagify.min.js") not in link_header

        user.is_staff = True
        user.save()
        response = client.get(reverse("boards:index-all"))
        link_header = response.get("Link")
        assert response.status_code == 200
        assert link_header is not None

        assert f"<{static('boards/js/index.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('boards/js/components/board_list.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('vendor/tagify-4.17.8/tagify.min.css')}>; rel=preload; as=style" in link_header
        assert f"<{static('vendor/tagify-4.17.8/tagify.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('vendor/tagify-4.17.8/tagify.polyfills.min.js')}>; rel=preload; as=script" in link_header
