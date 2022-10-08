from django.templatetags.static import static
from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import USER_TEST_PASSWORD, UserFactory


class BoardListLinkHeaderMixinTest(TestCase):
    def test_dispatch_anonymous(self):
        response = self.client.get(reverse("boards:index"))
        link_header = response.get("Link")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(link_header)

        self.assertIn(f"<{static('boards/js/index.js')}>; rel=preload; as=script", link_header)
        self.assertNotIn(static("boards/js/components/board_list.js"), link_header)
        self.assertNotIn(static("css/3rdparty/tagify-4.16.4.min.css"), link_header)
        self.assertNotIn(static("js/3rdparty/tagify-4.16.4.min.js"), link_header)

    def test_dispatch_authenticated(self):
        user = UserFactory()
        self.client.login(username=user, password=USER_TEST_PASSWORD)

        response = self.client.get(reverse("boards:index"))
        link_header = response.get("Link")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(link_header)

        self.assertIn(f"<{static('boards/js/index.js')}>; rel=preload; as=script", link_header)
        self.assertIn(f"<{static('boards/js/components/board_list.js')}>; rel=preload; as=script", link_header)
        self.assertNotIn(static("css/3rdparty/tagify-4.16.4.min.css"), link_header)
        self.assertNotIn(static("js/3rdparty/tagify-4.16.4.min.js"), link_header)

        user.is_staff = True
        user.save()
        response = self.client.get(reverse("boards:index-all"))
        link_header = response.get("Link")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(link_header)

        self.assertIn(f"<{static('boards/js/index.js')}>; rel=preload; as=script", link_header)
        self.assertIn(f"<{static('boards/js/components/board_list.js')}>; rel=preload; as=script", link_header)
        self.assertIn(f"<{static('css/3rdparty/tagify-4.16.4.min.css')}>; rel=preload; as=style", link_header)
        self.assertIn(f"<{static('js/3rdparty/tagify-4.16.4.min.js')}>; rel=preload; as=script", link_header)
        self.assertIn(
            f"<{static('js/3rdparty/tagify-4.16.4.polyfills.min.js')}>; rel=preload; as=script", link_header
        )
