from django.templatetags.static import static
from django.urls import reverse


class TestJotletLinkHeaderMixin:
    def test_dispatch(self, client):
        response = client.get(reverse("boards:index"))
        link_header = response.get("Link")
        assert response.status_code == 200
        assert link_header is not None

        assert f"<{static('css/vendor/bootstrap-5.3.0-alpha2.min.css')}>; rel=preload; as=style" in link_header
        assert f"<{static('css/vendor/bootstrap-icons-1.10.3.min.css')}>; rel=preload; as=style" in link_header
        assert f"<{static('css/styles.css')}>; rel=preload; as=style" in link_header
        assert (
            f"<{static('css/vendor/fonts/bootstrap-icons.woff2?8d200481aa7f02a2d63a331fc782cfaf')}>; rel=preload; as=font; crossorigin=anonymous"  # noqa: E501
            in link_header
        )
        assert f"<{static('js/color-mode-toggler.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/bootstrap-5.3.0-alpha2.bundle.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/htmx-1.8.5.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/base.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/htmx-alpine-morph-1.8.5.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/alpinejs-collapse-3.11.1.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/alpinejs-mask-3.11.1.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/alpinejs-morph-3.11.1.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/alpinejs-persist-3.11.1.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/alpinejs-3.11.1.min.js')}>; rel=preload; as=script" in link_header
