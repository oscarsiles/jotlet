from django.templatetags.static import static
from django.urls import reverse


class TestJotletLinkHeaderMixin:
    def test_dispatch(self, client):
        response = client.get(reverse("boards:index"))
        link_header = response.get("Link")
        assert response.status_code == 200
        assert link_header is not None

        assert f"<{static('css/3rdparty/bootstrap-5.2.2.min.css')}>; rel=preload; as=style" in link_header
        assert f"<{static('css/3rdparty/bootstrap-icons-1.10.1.min.css')}>; rel=preload; as=style" in link_header
        assert f"<{static('css/styles.css')}>; rel=preload; as=style" in link_header
        assert (
            f"<{static('css/3rdparty/fonts/bootstrap-icons.woff2?8d200481aa7f02a2d63a331fc782cfaf')}>; rel=preload; as=font; crossorigin=anonymous"  # noqa: E501
            in link_header
        )
        assert f"<{static('js/3rdparty/bootstrap-5.2.2.bundle.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/3rdparty/htmx-1.8.4.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/base.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/3rdparty/htmx-alpine-morph-1.8.4.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/3rdparty/alpinejs-collapse-3.10.4.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/3rdparty/alpinejs-mask-3.10.4.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/3rdparty/alpinejs-morph-3.10.4.min.js')}>; rel=preload; as=script" in link_header
        assert f"<{static('js/3rdparty/alpinejs-3.10.4.min.js')}>; rel=preload; as=script" in link_header
