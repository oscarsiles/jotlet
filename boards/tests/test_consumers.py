from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.test import TestCase

from boards.routing import websocket_urlpatterns

from .factories import BoardFactory


class BoardConsumerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.board = BoardFactory()

    async def test_session_connect_disconnect_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board_group_name = f"board_{self.board.slug}"
        self.assertEqual(await cache.aget(board_group_name), None)

        communicator1 = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator1.connect()
        self.assertTrue(connected, "Could not connect")
        await sync_to_async(self.client.login)(username="testuser1", password="1X<ISRUkw+tuK")
        message = await communicator1.receive_from()
        self.assertIn("session_connected", message)
        self.assertIn('"sessions": 1', message)
        self.assertEqual(await cache.aget(board_group_name), 1)

        communicator2 = WebsocketCommunicator(application, f"/ws/boards/{self.board.slug}/")
        connected, _ = await communicator2.connect()
        message = await communicator1.receive_from()
        self.assertIn("session_connected", message)
        self.assertIn('"sessions": 2', message)
        self.assertEqual(await cache.aget(board_group_name), 2)

        await communicator2.disconnect()
        message = await communicator1.receive_from()
        self.assertIn("session_disconnected", message)
        self.assertIn('"sessions": 1', message)
        self.assertEqual(await cache.aget(board_group_name), 1)

        await communicator1.disconnect()
        self.assertEqual(await cache.aget(board_group_name), None)
