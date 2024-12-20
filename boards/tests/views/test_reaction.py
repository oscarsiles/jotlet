from http import HTTPStatus

import pytest
from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.urls import reverse
from pytest_factoryboy import LazyFixture

from boards.models import REACTION_TYPE, BoardPreferences, Post, Reaction
from boards.routing import websocket_urlpatterns


class TestPostReactionView:
    @pytest.fixture(autouse=True)
    def _setup_method_fixture(self, board, topic, post):
        self.post_reaction_url = reverse(
            "boards:post-reaction", kwargs={"slug": board.slug, "topic_pk": topic.pk, "pk": post.pk}
        )

    @pytest.mark.parametrize("reaction_type", [reaction for reaction in REACTION_TYPE if reaction[0] != "n"])
    def test_post_reaction_repeat_anonymous(self, client, post, reaction_type):
        assert Reaction.objects.count() == 0

        post.topic.board.preferences.reaction_type = reaction_type[0]
        post.topic.board.preferences.save()

        response = client.post(self.post_reaction_url, {"score": 1})
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Reaction.objects.count() == 1

        response = client.post(self.post_reaction_url, {"score": 1})
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Reaction.objects.count() == 0

    @pytest.mark.parametrize(
        "reaction_type",
        [reaction for reaction in REACTION_TYPE if reaction[0] not in ["n", "l"]],
    )
    def test_post_reaction_score_changed(self, client, post, reaction_type):
        assert Reaction.objects.count() == 0

        post.topic.board.preferences.reaction_type = reaction_type[0]
        post.topic.board.preferences.save()

        first_score = 1
        second_score = 2
        response = client.post(self.post_reaction_url, {"score": first_score})
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Reaction.objects.count() == 1
        assert Reaction.objects.first().reaction_score == first_score

        response = client.post(self.post_reaction_url, {"score": second_score})
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Reaction.objects.count() == 1
        assert Reaction.objects.first().reaction_score == second_score

        Reaction.objects.filter(post=post).delete()

    def test_post_reaction_disabled(self, client):
        assert Reaction.objects.count() == 0

        response = client.post(self.post_reaction_url, {"score": 1})
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Reaction.objects.count() == 0

    @pytest.mark.parametrize("post__user", [LazyFixture("user")])
    @pytest.mark.parametrize("reaction_type", REACTION_TYPE[1:])
    def test_post_reaction_own_post(self, client, post, user, reaction_type):
        assert Reaction.objects.count() == 0

        client.force_login(user)

        reaction_type = reaction_type[0]
        post.topic.board.preferences.reaction_type = reaction_type
        post.topic.board.preferences.save()

        response = client.post(
            self.post_reaction_url,
            {"score": 1},
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Reaction.objects.count() == 0

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_reaction_updated_websocket_message(self, client, board, post):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        message = await communicator.receive_from()
        assert "session_connected" in message
        for _type in REACTION_TYPE[1:]:
            preferences = await BoardPreferences.objects.aget(board=board)
            preferences.reaction_type = _type[0]
            await preferences.asave()
            message = await communicator.receive_from()
            assert "board_preferences_changed" in message
            await sync_to_async(client.post)(self.post_reaction_url, data={"score": 1})
            message = await communicator.receive_from()
            assert "reaction_updated" in message
            assert f'"post_pk": "{post.pk!s}"' in message
        await communicator.disconnect()


class TestReactionsDeleteView:
    @pytest.fixture(autouse=True)
    def _setup_method(self, board, topic, post, user3, post_factory, reaction_factory):
        board.preferences.moderators.add(user3)
        board.preferences.reaction_type = "l"
        board.preferences.save()
        post_factory.create_batch(4, topic=topic)
        for p in Post.objects.all():
            for reaction_type in REACTION_TYPE[1:]:
                reaction_factory.create_batch(
                    5,
                    post=p,
                    reaction_type=reaction_type[0],
                    reaction_score="1",
                )
        post = Post.objects.first()
        self.reactions_delete_url = reverse(
            "boards:post-reactions-delete",
            kwargs={"slug": board.slug, "topic_pk": topic.pk, "pk": post.pk},
        )

    def test_anonymous_permissions(self, client):
        response = client.get(self.reactions_delete_url)
        assert response.status_code == HTTPStatus.FOUND
        assert Reaction.objects.count() == 25 * (len(REACTION_TYPE) - 1)

        response = client.post(self.reactions_delete_url)
        assert response.status_code == HTTPStatus.FOUND
        assert Reaction.objects.count() == 25 * (len(REACTION_TYPE) - 1)

    def test_other_user_permissions(self, client, user2):
        client.force_login(user2)
        response = client.get(self.reactions_delete_url)
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Reaction.objects.count() == 25 * (len(REACTION_TYPE) - 1)

        response = client.post(self.reactions_delete_url)
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Reaction.objects.count() == 25 * (len(REACTION_TYPE) - 1)

    def test_moderator_permissions(self, client, user3):
        client.force_login(user3)
        response = client.get(self.reactions_delete_url)
        assert response.status_code == HTTPStatus.OK
        assert Reaction.objects.count() == 25 * (len(REACTION_TYPE) - 1)

        response = client.post(self.reactions_delete_url)
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Reaction.objects.count() == 25 * (len(REACTION_TYPE) - 1) - 5

    def test_owner_permissions(self, client, user):
        client.force_login(user)
        response = client.get(self.reactions_delete_url)
        assert response.status_code == HTTPStatus.OK
        assert Reaction.objects.count() == 25 * (len(REACTION_TYPE) - 1)

        response = client.post(self.reactions_delete_url)
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Reaction.objects.count() == 25 * (len(REACTION_TYPE) - 1) - 5

    def test_no_reactions_preferences(self, client, board, user):
        board.preferences.reaction_type = "n"
        board.preferences.save()
        client.force_login(user)
        response = client.get(self.reactions_delete_url)
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Reaction.objects.count() == 25 * (len(REACTION_TYPE) - 1)

        response = client.post(self.reactions_delete_url)
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Reaction.objects.count() == 25 * (len(REACTION_TYPE) - 1)

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_post_toggle_websocket_message(self, client, board, user):
        post = await Post.objects.afirst()
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, _ = await communicator.connect()
        assert connected, "Could not connect"
        await sync_to_async(client.force_login)(user)
        message = await communicator.receive_from()
        assert "session_connected" in message
        await sync_to_async(client.post)(self.reactions_delete_url)
        message = await communicator.receive_from()
        assert "reaction_updated" in message
        assert f'"post_pk": "{post.pk!s}"' in message
        await communicator.disconnect()
