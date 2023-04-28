from django.templatetags.static import static
from django.urls import reverse


class TestJotletLinkHeaderMixin:
    def test_dispatch(self, client):
        response = client.get(reverse("boards:index"))
        link_header = response.get("Link")
        assert response.status_code == 200
        assert link_header is not None

        assert f"<{static('css/vendor/bootstrap-5.3.0-alpha3.min.css')}>; rel=preload; as=style" in link_header
        assert f"<{static('css/vendor/bootstrap-icons-1.10.5.min.css')}>; rel=preload; as=style" in link_header
        assert f"<{static('css/styles.css')}>; rel=preload; as=style" in link_header
        assert (
            f"<{static('css/vendor/fonts/bootstrap-icons.woff2?8d200481aa7f02a2d63a331fc782cfaf')}>; rel=preload; as=font; crossorigin=anonymous"  # noqa: E501
            in link_header
        )
        assert f"<{static('js/color-mode-toggler.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/bootstrap-5.3.0-alpha3.bundle.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/htmx-1.9.1/htmx.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/base.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/htmx-1.9.1/htmx-alpine-morph.min.js')}>; rel=preload; as=script" in link_header
        assert (
            f"<{static('js/vendor/alpinejs-3.12.0/alpinejs-collapse.min.js')}>; rel=preload; as=script" in link_header
        )
        assert f"<{static('js/vendor/alpinejs-3.12.0/alpinejs-mask.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/vendor/alpinejs-3.12.0/alpinejs-morph.min.js')}>; rel=preload; as=script" in link_header
        assert (
            f"<{static('js/vendor/alpinejs-3.12.0/alpinejs-persist.min.js')}>; rel=preload; as=script" in link_header
        )
        assert f"<{static('js/vendor/alpinejs-3.12.0/alpinejs.min.js')}>; rel=preload; as=script" in link_header
