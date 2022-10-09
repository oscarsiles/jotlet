from django.templatetags.static import static
from django.test import TestCase
from django.urls import reverse


class JotletLinkHeaderMixinTest(TestCase):
    def test_dispatch(self):
        response = self.client.get(reverse("boards:index"))
        link_header = response.get("Link")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(link_header)

        self.assertIn(f"<{static('css/3rdparty/bootstrap-5.2.2.min.css')}>; rel=preload; as=style", link_header)
        self.assertIn(f"<{static('css/3rdparty/bootstrap-icons-1.9.1.min.css')}>; rel=preload; as=style", link_header)
        self.assertIn(f"<{static('css/styles.css')}>; rel=preload; as=style", link_header)
        self.assertIn(
            f"<{static('css/3rdparty/fonts/bootstrap-icons.woff2?8d200481aa7f02a2d63a331fc782cfaf')}>; rel=preload; as=font; crossorigin=anonymous",  # noqa: E501
            link_header,
        )
        self.assertIn(f"<{static('js/3rdparty/bootstrap-5.2.2.bundle.min.js')}>; rel=preload; as=script", link_header)
        self.assertIn(f"<{static('js/3rdparty/htmx-1.8.0.min.js')}>; rel=preload; as=script", link_header)
        self.assertIn(f"<{static('js/base.js')}>; rel=preload; as=script", link_header)
        self.assertIn(
            f"<{static('js/3rdparty/alpinejs-collapse-3.10.4.min.js')}>; rel=preload; as=script", link_header
        )
        self.assertIn(f"<{static('js/3rdparty/alpinejs-mask-3.10.4.min.js')}>; rel=preload; as=script", link_header)
        self.assertIn(f"<{static('js/3rdparty/alpinejs-morph-3.10.4.min.js')}>; rel=preload; as=script", link_header)
        self.assertIn(f"<{static('js/3rdparty/alpinejs-3.10.4.min.js')}>; rel=preload; as=script", link_header)
