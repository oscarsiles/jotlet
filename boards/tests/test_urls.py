from django.test import TestCase
from django.urls import resolve, reverse


class UrlsTest(TestCase):
    def test_reverse_url(self):
        url = reverse("boards:index")
        self.assertEqual(url, "/boards/")

        url = reverse("boards:board-create")
        self.assertEqual(url, "/boards/create/")

        url = reverse("boards:image-select", kwargs={"type": "type"})
        self.assertEqual(url, "/boards/image_select/type/")

        url = reverse("boards:board", kwargs={"slug": "slug"})
        self.assertEqual(url, "/boards/slug/")

        url = reverse("boards:board-update", kwargs={"slug": "slug"})
        self.assertEqual(url, "/boards/slug/update/")

        url = reverse("boards:board-delete", kwargs={"slug": "slug"})
        self.assertEqual(url, "/boards/slug/delete/")

        url = reverse("boards:board-fetch", kwargs={"slug": "slug"})
        self.assertEqual(url, "/boards/slug/fetch/")

        url = reverse("boards:board-qr", kwargs={"slug": "slug"})
        self.assertEqual(url, "/boards/slug/qr/")

        url = reverse("boards:board-preferences", kwargs={"slug": "slug"})
        self.assertEqual(url, "/boards/slug/preferences/")

        url = reverse("boards:topic-create", kwargs={"slug": "slug"})
        self.assertEqual(url, "/boards/slug/topics/create/")

        url = reverse("boards:topic-update", kwargs={"slug": "slug", "pk": 1})
        self.assertEqual(url, "/boards/slug/topics/1/update/")

        url = reverse("boards:topic-delete", kwargs={"slug": "slug", "pk": 1})
        self.assertEqual(url, "/boards/slug/topics/1/delete/")

        url = reverse("boards:topic-fetch", kwargs={"slug": "slug", "pk": 1})
        self.assertEqual(url, "/boards/slug/topics/1/fetch/")

        url = reverse("boards:post-create", kwargs={"slug": "slug", "topic_pk": 1})
        self.assertEqual(url, "/boards/slug/topics/1/posts/create/")

        url = reverse("boards:post-update", kwargs={"slug": "slug", "pk": 1})
        self.assertEqual(url, "/boards/slug/posts/1/update/")

        url = reverse("boards:post-delete", kwargs={"slug": "slug", "pk": 1})
        self.assertEqual(url, "/boards/slug/posts/1/delete/")

        url = reverse("boards:post-fetch", kwargs={"slug": "slug", "pk": 1})
        self.assertEqual(url, "/boards/slug/posts/1/fetch/post/")

        url = reverse("boards:post-footer-fetch", kwargs={"slug": "slug", "pk": 1})
        self.assertEqual(url, "/boards/slug/posts/1/fetch/footer/")

        url = reverse("boards:post-toggle-approval", kwargs={"slug": "slug", "pk": 1})
        self.assertEqual(url, "/boards/slug/posts/1/approval/")

        url = reverse("boards:post-reaction", kwargs={"slug": "slug", "pk": 1})
        self.assertEqual(url, "/boards/slug/posts/1/reaction/")

    def test_resolve_url(self):
        resolver = resolve("/boards/")
        self.assertEqual(resolver.view_name, "boards:index")

        resolver = resolve("/boards/create/")
        self.assertEqual(resolver.view_name, "boards:board-create")

        resolver = resolve("/boards/image_select/type/")
        self.assertEqual(resolver.view_name, "boards:image-select")

        resolver = resolve("/boards/slug/")
        self.assertEqual(resolver.view_name, "boards:board")

        resolver = resolve("/boards/slug/update/")
        self.assertEqual(resolver.view_name, "boards:board-update")

        resolver = resolve("/boards/slug/delete/")
        self.assertEqual(resolver.view_name, "boards:board-delete")

        resolver = resolve("/boards/slug/fetch/")
        self.assertEqual(resolver.view_name, "boards:board-fetch")

        resolver = resolve("/boards/slug/qr/")
        self.assertEqual(resolver.view_name, "boards:board-qr")

        resolver = resolve("/boards/slug/preferences/")
        self.assertEqual(resolver.view_name, "boards:board-preferences")

        resolver = resolve("/boards/slug/topics/create/")
        self.assertEqual(resolver.view_name, "boards:topic-create")

        resolver = resolve("/boards/slug/topics/1/update/")
        self.assertEqual(resolver.view_name, "boards:topic-update")

        resolver = resolve("/boards/slug/topics/1/delete/")
        self.assertEqual(resolver.view_name, "boards:topic-delete")

        resolver = resolve("/boards/slug/topics/1/fetch/")
        self.assertEqual(resolver.view_name, "boards:topic-fetch")

        resolver = resolve("/boards/slug/topics/1/posts/create/")
        self.assertEqual(resolver.view_name, "boards:post-create")

        resolver = resolve("/boards/slug/posts/1/update/")
        self.assertEqual(resolver.view_name, "boards:post-update")

        resolver = resolve("/boards/slug/posts/1/delete/")
        self.assertEqual(resolver.view_name, "boards:post-delete")

        resolver = resolve("/boards/slug/posts/1/fetch/post/")
        self.assertEqual(resolver.view_name, "boards:post-fetch")

        resolver = resolve("/boards/slug/posts/1/fetch/footer/")
        self.assertEqual(resolver.view_name, "boards:post-footer-fetch")

        resolver = resolve("/boards/slug/posts/1/approval/")
        self.assertEqual(resolver.view_name, "boards:post-toggle-approval")

        resolver = resolve("/boards/slug/posts/1/reaction/")
        self.assertEqual(resolver.view_name, "boards:post-reaction")
