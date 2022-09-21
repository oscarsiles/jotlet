from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import USER_TEST_PASSWORD, UserFactory
from boards.models import Topic
from boards.routing import websocket_urlpatterns
from boards.tests.factories import BoardFactory, TopicFactory


class TopicCreateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.topic_created_url = reverse("boards:topic-create", kwargs={"slug": cls.board.slug})

    def test_anonymous_permissions(self):
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_staff_permissions(self):
        staff_user = UserFactory(is_staff=True)
        self.client.login(username=staff_user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(reverse("boards:topic-create", kwargs={"slug": self.board.slug}))
        self.assertEqual(response.status_code, 200)

    def test_topic_create_success(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:topic-create", kwargs={"slug": self.board.slug}),
            data={"subject": "Test Topic"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertIsNotNone(Topic.objects.get(subject="Test Topic"))

    def test_topic_create_blank(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:topic-create", kwargs={"slug": self.board.slug}),
            data={"subject": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "subject", "This field is required.")

    def test_topic_create_invalid(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:topic-create", kwargs={"slug": self.board.slug}),
            data={"subject": "x" * 401},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "subject", "Ensure this value has at most 400 characters (it has 401)."
        )

    async def test_topic_created_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.topic_created_url, data={"subject": "Test Topic"})
        topic = await sync_to_async(Topic.objects.get)(subject="Test Topic")
        message = await communicator.receive_from()
        self.assertIn("topic_created", message)
        self.assertIn(f'"topic_pk": {topic.id}', message)


class TopicUpdateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.topic = TopicFactory(board=cls.board)
        cls.topic_updated_url = reverse("boards:topic-update", kwargs={"slug": cls.board.slug, "pk": cls.topic.pk})

    def test_anonymous_permissions(self):
        response = self.client.get(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_staff_permissions(self):
        staff_user = UserFactory(is_staff=True)
        self.client.login(username=staff_user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_topic_update_success(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk}),
            data={"subject": "Test Topic NEW"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertIsNotNone(Topic.objects.get(subject="Test Topic NEW"))

    def test_topic_update_blank(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk}),
            data={"subject": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "subject", "This field is required.")

    def test_topic_update_invalid(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.post(
            reverse("boards:topic-update", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk}),
            data={"subject": "x" * 401},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "subject", "Ensure this value has at most 400 characters (it has 401)."
        )

    async def test_topic_updated_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.topic_updated_url, data={"subject": "Test Topic NEW"})
        message = await communicator.receive_from()
        self.assertIn("topic_updated", message)
        self.assertIn(f'"topic_pk": {self.topic.pk}', message)


class TopicDeleteViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.topic = TopicFactory(board=cls.board)
        cls.topic_deleted_url = reverse("boards:topic-delete", kwargs={"slug": cls.board.slug, "pk": cls.topic.pk})

    def test_anonymous_permissions(self):
        response = self.client.get(
            reverse("boards:topic-delete", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:topic-delete", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:topic-delete", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("boards:topic-delete", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertRaises(Topic.DoesNotExist, Topic.objects.get, pk=self.topic.pk)
        self.assertEqual(response.status_code, 204)

    def test_staff_permissions(self):
        staff_user = UserFactory(is_staff=True)
        self.client.login(username=staff_user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(
            reverse("boards:topic-delete", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("boards:topic-delete", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertRaises(Topic.DoesNotExist, Topic.objects.get, pk=self.topic.pk)
        self.assertEqual(response.status_code, 204)

    async def test_topic_deleted_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.topic_deleted_url)
        message = await communicator.receive_from()
        self.assertIn("topic_deleted", message)
        self.assertIn(f'"topic_pk": {self.topic.pk}', message)


class TopicFetchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.topic = TopicFactory()

    def test_topic_fetch(self):
        response = self.client.get(
            reverse("boards:topic-fetch", kwargs={"slug": self.topic.board.slug, "pk": self.topic.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["topic"], self.topic)
