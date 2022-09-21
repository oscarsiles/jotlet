from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import USER_TEST_PASSWORD, UserFactory
from boards.models import REACTION_TYPE, BoardPreferences, Post, Reaction
from boards.routing import websocket_urlpatterns
from boards.tests.factories import BoardFactory, PostFactory, ReactionFactory, TopicFactory


class PostReactionViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.board = BoardFactory(owner=cls.user)
        cls.topic = TopicFactory(board=cls.board)
        cls.post = PostFactory(topic=cls.topic, user=cls.user)
        cls.post_reaction_url = reverse(
            "boards:post-reaction", kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk}
        )

    def test_post_reaction_repeat_anonymous(self):
        self.assertEqual(Reaction.objects.count(), 0)

        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            self.post.topic.board.preferences.reaction_type = type
            self.post.topic.board.preferences.save()

            response = self.client.post(self.post_reaction_url, {"score": 1})
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 1)

            response = self.client.post(self.post_reaction_url, {"score": 1})
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 0)

    def test_post_reaction_score_changed(self):
        self.assertEqual(Reaction.objects.count(), 0)

        for _type in REACTION_TYPE[2:]:  # like only has one score
            type = _type[0]
            self.post.topic.board.preferences.reaction_type = type
            self.post.topic.board.preferences.save()
            if type == "v":
                second_score = -1
            elif type == "s":
                second_score = 2

            response = self.client.post(self.post_reaction_url, {"score": 1})
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 1)
            self.assertEqual(Reaction.objects.first().reaction_score, 1)

            response = self.client.post(self.post_reaction_url, {"score": second_score})
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 1)
            self.assertEqual(Reaction.objects.first().reaction_score, second_score)

            Reaction.objects.filter(post=self.post).delete()

    def test_post_reaction_disabled(self):
        self.assertEqual(Reaction.objects.count(), 0)

        response = self.client.post(self.post_reaction_url, {"score": 1})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Reaction.objects.count(), 0)

    def test_post_reaction_own_post(self):
        self.assertEqual(Reaction.objects.count(), 0)

        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)

        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            self.post.topic.board.preferences.reaction_type = type
            self.post.topic.board.preferences.save()

            response = self.client.post(
                self.post_reaction_url,
                {"score": 1},
            )
            self.assertEqual(response.status_code, 204)
            self.assertEqual(Reaction.objects.count(), 0)

    async def test_reaction_updated_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        for _type in REACTION_TYPE[1:]:
            type = _type[0]
            preferences = await sync_to_async(BoardPreferences.objects.get)(board=self.board)
            preferences.reaction_type = type
            await sync_to_async(preferences.save)()
            message = await communicator.receive_from()
            self.assertIn("board_preferences_changed", message)
            await sync_to_async(self.client.post)(self.post_reaction_url, data={"score": 1})
            message = await communicator.receive_from()
            self.assertIn("reaction_updated", message)
            self.assertIn(f'"post_pk": {self.post.pk}', message)


class ReactionsDeleteViewTest(TestCase):
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
        PostFactory.create_batch(5, topic=cls.topic)
        for post in Post.objects.all():
            for type in REACTION_TYPE[1:]:
                ReactionFactory.create_batch(
                    5,
                    post=post,
                    type=type[0],
                    reaction_score="1",
                )
        cls.post = Post.objects.first()
        cls.reactions_delete_url = reverse(
            "boards:post-reactions-delete",
            kwargs={"slug": cls.board.slug, "topic_pk": cls.topic.pk, "pk": cls.post.pk},
        )

    def test_anonymous_permissions(self):
        response = self.client.get(self.reactions_delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

        response = self.client.post(self.reactions_delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

    def test_other_user_permissions(self):
        self.client.login(username=self.user2.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.reactions_delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

        response = self.client.post(self.reactions_delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

    def test_moderator_permissions(self):
        self.client.login(username=self.user3.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.reactions_delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

        response = self.client.post(self.reactions_delete_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1) - 5)

    def test_owner_permissions(self):
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.reactions_delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

        response = self.client.post(self.reactions_delete_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1) - 5)

    def test_no_reactions_preferences(self):
        self.board.preferences.reaction_type = "n"
        self.board.preferences.save()
        self.client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        response = self.client.get(self.reactions_delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

        response = self.client.post(self.reactions_delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Reaction.objects.count(), 25 * (len(REACTION_TYPE) - 1))

    async def test_post_toggle_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username=self.user.username, password=USER_TEST_PASSWORD)
        message = await communicator.receive_from()
        self.assertIn("session_connected", message)
        await sync_to_async(self.client.post)(self.reactions_delete_url)
        message = await communicator.receive_from()
        self.assertIn("reaction_updated", message)
        self.assertIn(f'"post_pk": {self.post.pk}', message)
