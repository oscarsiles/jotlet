from django.templatetags.static import static
from django.urls import reverse


class TestJotletLinkHeaderMixin:
    def test_dispatch(self, client):
        response = client.get(reverse("boards:index"))
        link_header = response.get("Link")
        assert response.status_code == 200
        assert link_header is not None

        assert f"<{static('vendor/bootstrap-5.3.0/css/bootstrap.min.css')}>; rel=preload; as=style" in link_header
        assert (
            f"<{static('vendor/bootstrap-icons-1.10.5/bootstrap-icons.min.css')}>; rel=preload; as=style"
            in link_header
        )
        assert f"<{static('css/styles.css')}>; rel=preload; as=style" in link_header
        assert (
            f"<{static('vendor/bootstrap-icons-1.10.5/fonts/bootstrap-icons.woff2?8d200481aa7f02a2d63a331fc782cfaf')}>; rel=preload; as=font; crossorigin=anonymous"  # noqa: E501
            in link_header
        )
        assert f"<{static('js/color-mode-toggler.js')}>; rel=preload; as=script" in link_header
        assert (
            f"<{static('vendor/bootstrap-5.3.0/js/bootstrap.bundle.min.js')}>; rel=preload; as=script" in link_header
        )
        assert f"<{static('vendor/htmx-1.9.2/htmx.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/base.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('vendor/htmx-1.9.2/htmx-alpine-morph.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('vendor/alpinejs-3.12.1/alpinejs-collapse.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('vendor/alpinejs-3.12.1/alpinejs-mask.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('vendor/alpinejs-3.12.1/alpinejs-morph.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('vendor/alpinejs-3.12.1/alpinejs-persist.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('vendor/alpinejs-3.12.1/alpinejs.min.js')}>; rel=preload; as=script" in link_header
