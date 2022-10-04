import json
import shutil
import tempfile

from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import timedelta

from accounts.tests.factories import USER_TEST_PASSWORD, UserFactory
from boards.models import REACTION_TYPE, Image, Post
from boards.routing import websocket_urlpatterns
from boards.tests.factories import BoardFactory, PostFactory, ReactionFactory, TopicFactory
from boards.tests.utils import create_image

MEDIA_ROOT = tempfile.mkdtemp()


class PostCreateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        cls.post_create_url = reverse("boards:post-create", kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk})

    def test_anonymous_permissions(self):
        response = self.client.get(self.post_create_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.post_create_url, data={"content": "Test Message anon"})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.first().content, "Test Message anon")

    def test_replies_permissions_anonymous(self):
        post = PostFactory(topic=self.topic)
        reply_url = reverse(
            "boards:post-reply",
            kwargs={"slug": self.topic.board.slug, "topic_pk": self.topic.pk, "post_pk": post.pk},
        )
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 302)

        self.topic.board.preferences.type = "r"
        self.topic.board.preferences.save()
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 302)

        self.topic.board.preferences.allow_guest_replies = True
        self.topic.board.preferences.save()
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 200)

        post.approved = False
        post.save()
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 302)

    def test_replies_permissions_owner(self):
        post = PostFactory(topic=self.topic)
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        reply_url = reverse(
            "boards:post-reply",
            kwargs={"slug": self.topic.board.slug, "topic_pk": self.topic.pk, "post_pk": post.pk},
        )
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 403)

        self.topic.board.preferences.type = "r"
        self.topic.board.preferences.save()
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 200)

        post.approved = False
        post.save()
        response = self.client.get(reply_url)
        self.assertEqual(response.status_code, 200)

    def test_reply(self):
        post = PostFactory(topic=self.topic)
        reply_url = reverse(
            "boards:post-reply",
            kwargs={"slug": self.topic.board.slug, "topic_pk": self.topic.pk, "post_pk": post.pk},
        )
        self.topic.board.preferences.type = "r"
        self.topic.board.preferences.allow_guest_replies = True
        self.topic.board.preferences.save()

        self.client.post(reply_url, data={"content": "Test Message reply"})
        reply = Post.objects.get(content="Test Message reply")
        self.assertEqual(reply.topic, self.topic)
        self.assertEqual(reply.parent, post)

    def test_post_session_key(self):
        self.client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        self.assertEqual(self.client.session.session_key, Post.objects.get(content="Test Post").session_key)

    def test_post_approval(self):
        self.board.preferences.require_post_approval = True
        self.board.preferences.save()
        self.client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        self.assertEqual(Post.objects.get(content="Test Post").approved, False)

        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        self.client.post(
            self.post_create_url,
            data={"content": "Test Post user1"},
        )
        self.assertEqual(
            Post.objects.get(content="Test Post user1").approved, True
        )  # Board owner can post without approval

        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        self.client.post(
            self.post_create_url,
            data={"content": "Test Post user2"},
        )
        self.assertEqual(Post.objects.get(content="Test Post user2").approved, False)  # Normal user needs approval

        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        self.client.post(
            self.post_create_url,
            data={"content": "Test Post user3"},
        )
        self.assertEqual(
            Post.objects.get(content="Test Post user3").approved, True
        )  # Moderator can post without approval

    def test_post_before_allowed(self):
        self.board.preferences.posting_allowed_from = timezone.now() + timedelta(days=1)
        self.board.preferences.save()
        response = self.client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRaises(Post.DoesNotExist, Post.objects.get, content="Test Post")

    def test_post_after_allowed(self):
        self.board.preferences.posting_allowed_until = timezone.now() - timedelta(days=1)
        self.board.preferences.save()
        response = self.client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRaises(Post.DoesNotExist, Post.objects.get, content="Test Post")

    def test_post_allowed_time(self):
        self.board.preferences.posting_allowed_from = timezone.now() - timedelta(days=1)
        self.board.preferences.posting_allowed_until = None
        self.board.preferences.save()
        response = self.client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.count(), 1)

        self.board.preferences.posting_allowed_from = None
        self.board.preferences.posting_allowed_until = timezone.now() + timedelta(days=1)
        self.board.preferences.save()
        response = self.client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.count(), 2)

        self.board.preferences.posting_allowed_from = timezone.now() - timedelta(days=1)
        self.board.preferences.posting_allowed_until = timezone.now() + timedelta(days=1)
        self.board.preferences.save()
        response = self.client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.count(), 3)

        self.board.preferences.posting_allowed_from = timezone.now() - timedelta(days=1)
        self.board.preferences.posting_allowed_until = timezone.now() - timedelta(days=2)
        self.board.preferences.save()
        response = self.client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.count(), 4)

        self.board.preferences.posting_allowed_from = timezone.now() + timedelta(days=2)
        self.board.preferences.posting_allowed_until = timezone.now() + timedelta(days=1)
        self.board.preferences.save()
        response = self.client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.count(), 5)

    def test_post_outside_window(self):
        self.board.preferences.posting_allowed_from = timezone.now() + timedelta(days=1)
        self.board.preferences.posting_allowed_until = timezone.now() + timedelta(days=2)
        self.board.preferences.save()
        response = self.client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRaises(Post.DoesNotExist, Post.objects.get, content="Test Post")

        self.board.preferences.posting_allowed_from = timezone.now() + timedelta(days=1)
        self.board.preferences.posting_allowed_until = timezone.now() - timedelta(days=1)
        self.board.preferences.save()
        response = self.client.post(
            self.post_create_url,
            data={"content": "Test Post"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRaises(Post.DoesNotExist, Post.objects.get, content="Test Post")

    async def test_post_created_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.post_create_url, data={"content": "Test Post"})
        post = await sync_to_async(Post.objects.get)(content="Test Post")
        self.assertIsNotNone(post)
        message = await communicator.receive_from()
        self.assertIn("post_created", message)
        self.assertIn(f'"topic_pk": {self.topic.pk}', message)


class PostUpdateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        cls.post = PostFactory(topic=cls.topic)
        cls.post_updated_url = reverse(
            "boards:post-update", kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk}
        )

    def test_anonymous_permissions(self):
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk}),
            data={"content": "Test Post anon"},
        )
        post = Post.objects.get(content="Test Post anon")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.session.session_key, post.session_key)
        response = self.client.post(
            reverse("boards:post-update", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": post.pk}),
            data={"content": "Test Post anon NEW"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.get(pk=post.pk).content, "Test Post anon NEW")

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse(
                "boards:post-update", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_board_moderator_permissions(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse(
                "boards:post-update", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            )
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse(
                "boards:post-update", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            ),
            data={"content": "Test Post NEW"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.get(pk=self.post.pk).content, "Test Post NEW")

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse(
                "boards:post-update", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            )
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse(
                "boards:post-update", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": self.post.pk}
            ),
            data={"content": "Test Post NEW"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.get(pk=self.post.pk).content, "Test Post NEW")

    async def test_post_updated_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.post_updated_url, data={"content": "Test Post NEW"})
        message = await communicator.receive_from()
        self.assertIn("post_updated", message)
        self.assertIn(f'"post_pk": {self.post.pk}', message)


class PostDeleteViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        cls.post = PostFactory(topic=cls.topic)
        cls.post_deleted_url = reverse(
            "boards:post-delete", kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk}
        )

    def test_anonymous_permissions(self):
        self.client.post(self.post_deleted_url)
        self.assertEqual(Post.objects.count(), 1)
        self.client.post(
            reverse("boards:post-create", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk}),
            data={"content": "Test Post anon"},
        )
        post2 = Post.objects.get(content="Test Post anon")
        self.assertEqual(Post.objects.count(), 2)
        self.client.post(
            reverse("boards:post-delete", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": post2.pk})
        )
        self.assertEqual(Post.objects.count(), 1)

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.post(self.post_deleted_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Post.objects.count(), 1)

    def test_board_moderator_permissions(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        response = self.client.post(self.post_deleted_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.count(), 0)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(self.post_deleted_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.count(), 0)

    async def test_post_deleted_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.post_deleted_url)
        message = await communicator.receive_from()
        self.assertIn("post_deleted", message)
        self.assertIn(f'"post_pk": {self.post.pk}', message)


class DeletePostsViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.topic = TopicFactory(board=cls.board)
        cls.topic2 = TopicFactory(board=cls.board)
        cls.topic_posts_delete_url = reverse(
            "boards:topic-posts-delete", kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk}
        )
        cls.board_posts_delete_url = reverse("boards:board-posts-delete", kwargs={"slug": cls.board.slug})
        PostFactory.create_batch(10, topic=cls.topic, user=cls.user)
        PostFactory.create_batch(10, topic=cls.topic2, user=cls.user2)

    def test_anonymous_permissions(self):
        response = self.client.get(self.topic_posts_delete_url)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(self.board_posts_delete_url)
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.topic_posts_delete_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(self.board_posts_delete_url)
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.topic_posts_delete_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.board_posts_delete_url)
        self.assertEqual(response.status_code, 200)

    def test_topic_posts_delete(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        self.assertEqual(Post.objects.filter(topic__board=self.board).count(), 20)
        response = self.client.post(self.topic_posts_delete_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.filter(topic=self.topic).count(), 0)
        self.assertEqual(Post.objects.filter(topic__board=self.board).count(), 10)

    def test_board_posts_delete(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        self.assertEqual(Post.objects.filter(topic__board=self.board).count(), 20)
        response = self.client.post(self.board_posts_delete_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.filter(topic__board=self.board).count(), 0)

    async def test_topic_posts_deleted_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.topic_posts_delete_url)
        for _ in range(10):
            message = await communicator.receive_from()
            self.assertIn("post_deleted", message)


class PostFetchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.require_post_approval = True
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        cls.post = PostFactory(topic=cls.topic, approved=False)
        cls.post_fetch_url = reverse(
            "boards:post-fetch", kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk}
        )

    def test_post_fetch_require_no_approval(self):
        self.board.preferences.require_post_approval = False
        self.board.preferences.save()
        response = self.client.get(self.post_fetch_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["post"], self.post)
        self.assertContains(response, self.post.content, html=True)

    def test_post_fetch_approved(self):
        self.board.preferences.require_post_approval = True
        self.board.preferences.save()
        self.post.approved = True
        self.post.save()
        response = self.client.get(self.post_fetch_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["post"], self.post)
        self.assertContains(response, self.post.content, html=True)

    def test_post_fetch_content_anonymous_not_approved(self):
        self.client.get(reverse("boards:board", kwargs={"slug": self.board.slug}))
        response = self.client.get(self.post_fetch_url)
        self.assertNotContains(response, self.post.content, html=True)

    def test_post_fetch_content_anonymous_not_approved_own_post(self):
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk}),
            data={"content": "Test Post anon"},
        )
        self.assertEqual(response.status_code, 204)
        post = Post.objects.get(content="Test Post anon")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": post.pk})
        )
        self.assertContains(response, post.content, html=True)

    def test_post_fetch_content_other_user_not_approved(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        self.client.get(reverse("boards:board", kwargs={"slug": self.board.slug}))

        response = self.client.get(self.post_fetch_url)
        self.assertNotContains(response, self.post.content, html=True)

    def test_post_fetch_content_other_user_not_approved_own_post(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:post-create", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk}),
            data={"content": "Test Post anon"},
        )
        self.assertEqual(response.status_code, 204)
        post = Post.objects.get(content="Test Post anon")
        response = self.client.get(
            reverse("boards:post-fetch", kwargs={"slug": self.board.slug, "topic_pk": self.topic.pk, "pk": post.pk})
        )
        self.assertContains(response, post.content, html=True)

    def test_post_fetch_content_board_moderator_not_approved(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.post_fetch_url)
        self.assertContains(response, self.post.content, html=True)

    def test_post_fetch_content_owner_not_approved(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.post_fetch_url)
        self.assertContains(response, self.post.content, html=True)

    def test_post_fetch_content_can_approve_not_approved(self):
        user4 = UserFactory()
        user4.user_permissions.add(Permission.objects.get(codename="can_approve_posts"))
        self.client.login(username=user4.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.post_fetch_url)
        self.assertContains(response, self.post.content, html=True)


class PostFooterFetchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.reaction_type = "l"
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        cls.post = PostFactory(topic=cls.topic, approved=True)
        for type in REACTION_TYPE[1:]:
            ReactionFactory(post=cls.post, type=type[0], user=cls.user)
        cls.post_footer_fetch_url = reverse(
            "boards:post-footer-fetch",
            kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk},
        )

    def test_post_footer_fetch_anonymous(self):
        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            if type == "l":
                icon = "bi-heart"
            elif type == "v":
                icon = "bi-hand-thumbs-up"
            elif type == "s":
                icon = "bi-star"

            self.post.topic.board.preferences.reaction_type = type
            self.post.topic.board.preferences.save()
            self.post.approved = False
            self.post.save()

            response = self.client.get(self.post_footer_fetch_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["post"], self.post)
            self.assertNotContains(response, icon)

            self.post.approved = True
            self.post.save()
            response = self.client.get(self.post_footer_fetch_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["post"], self.post)
            self.assertContains(response, icon)

    def test_post_footer_fetch_moderator(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        post = Post.objects.get(pk=self.post.pk)
        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            if type == "l":
                icon = "bi-heart"
            elif type == "v":
                icon = "bi-hand-thumbs-up"
            elif type == "s":
                icon = "bi-star"

            post.topic.board.preferences.reaction_type = type
            post.topic.board.preferences.save()
            post.approved = False
            post.save()

            response = self.client.get(self.post_footer_fetch_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["post"], post)
            self.assertContains(response, icon)

            post.approved = True
            post.save()
            response = self.client.get(self.post_footer_fetch_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["post"], post)
            self.assertContains(response, icon)


class PostToggleApprovalViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.board.preferences.moderators.add(cls.user3)
        cls.board.preferences.require_post_approval = True
        cls.board.preferences.save()
        cls.topic = TopicFactory(board=cls.board)
        cls.post = PostFactory(topic=cls.topic, approved=False)
        cls.post_approval_url = reverse(
            "boards:post-toggle-approval",
            kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk},
        )

    def test_post_toggle_approval_anonymous(self):
        self.assertFalse(self.post.approved)
        response = self.client.post(self.post_approval_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Post.objects.get(pk=self.post.pk).approved)

    def test_post_toggle_approval_other_user(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        self.assertFalse(self.post.approved)
        response = self.client.post(self.post_approval_url)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Post.objects.get(pk=self.post.pk).approved)

    def test_post_toggle_approval_board_moderator(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        self.assertFalse(self.post.approved)
        response = self.client.post(self.post_approval_url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Post.objects.get(pk=self.post.pk).approved)
        response = self.client.post(self.post_approval_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Post.objects.get(pk=self.post.pk).approved)

    def test_post_toggle_approval_owner(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        self.assertFalse(self.post.approved)
        response = self.client.post(self.post_approval_url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Post.objects.get(pk=self.post.pk).approved)
        response = self.client.post(self.post_approval_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Post.objects.get(pk=self.post.pk).approved)

    async def test_post_toggle_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.post_approval_url)
        message = await communicator.receive_from()
        self.assertIn("post_updated", message)
        self.assertIn(f'"post_pk": {self.post.pk}', message)
        await sync_to_async(self.client.post)(self.post_approval_url)
        message = await communicator.receive_from()
        self.assertIn("post_updated", message)
        self.assertIn(f'"post_pk": {self.post.pk}', message)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PostImageUploadViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.board = BoardFactory()
        cls.board.preferences.allow_image_uploads = True
        cls.board.preferences.save()
        cls.upload_url = reverse("boards:post-image-upload", kwargs={"slug": cls.board.slug})

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_permissions(self):
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, 405)

        valid_image_types = ["image/png", "image/jpeg", "image/bmp", "image/webp"]
        for image_type in valid_image_types:
            response = self.client.post(
                self.upload_url,
                {
                    "image": SimpleUploadedFile(
                        "test.png",
                        create_image(image_type.split("/")[1]),
                        content_type=image_type,
                    )
                },
            )
            self.assertEqual(response.status_code, 200)
            image = Image.objects.order_by("created_at").last()
            data = json.loads(response.content)
            self.assertEqual(data["data"]["filePath"], image.image.url)

        self.board.preferences.allow_image_uploads = False
        self.board.preferences.save()

        response = self.client.post(self.upload_url)
        self.assertEqual(response.status_code, 302)

    def test_upload_image_over_max_count(self):
        for i in range(settings.MAX_POST_IMAGE_COUNT + 1):
            response = self.client.post(
                self.upload_url,
                {"image": SimpleUploadedFile(f"test{i}.png", create_image("png"), content_type="image/png")},
            )
            data = json.loads(response.content)
            if i < settings.MAX_POST_IMAGE_COUNT:
                self.assertEqual(data["data"]["filePath"], Image.objects.order_by("created_at").last().image.url)
            else:
                self.assertEqual(data["error"], "Board image quota exceeded")

    def test_upload_invalid_image(self):
        response = self.client.post(
            self.upload_url,
            {"image": SimpleUploadedFile("test.avif", create_image("avif"), content_type="image/avif")},
        )
        data = json.loads(response.content)
        self.assertEqual(data["error"], "Invalid image type (only PNG, JPEG, GIF, BMP, and WEBP are allowed)")
