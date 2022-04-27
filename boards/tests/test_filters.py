from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils import timezone

from boards.filters import BoardFilter
from boards.models import Board


class BoardFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user1 = User.objects.create_user(username="testuser1", password="1X<ISRUkw+tuK")
        user2 = User.objects.create_user(username="testuser2", password="2HJ1vRV0Z&3iD")
        yesterday = timezone.now() - timedelta(days=1)
        board1 = Board.objects.create(title="Test Board 1", slug="000001", owner=user1)
        board1.created_at = yesterday
        board1.save()
        Board.objects.create(title="Test Board 2", slug="000002", owner=user1)
        Board.objects.create(title="Test Board 3", slug="000003", owner=user2)

    def setUp(self):
        self.factory = RequestFactory()

    def test_board_filter(self):
        user1 = User.objects.get(username="testuser1")
        user2 = User.objects.get(username="testuser2")
        request = self.factory.get(reverse("boards:board-list"))
        request.user = user1
        request.GET = request.GET.copy()
        request.GET["q"] = ""
        request.GET["after"] = ""
        request.GET["before"] = ""
        request.GET["owner"] = "testuser2"
        filterset = BoardFilter(request.GET, request=request)
        self.assertEqual(filterset.qs.count(), 2)

        request.GET["q"] = "Test Board 1"
        filterset = BoardFilter(request.GET, request=request)
        self.assertEqual(filterset.qs.count(), 1)
        request.GET["q"] = ""

        request.GET["before"] = date.today().strftime("%Y-%m-%d")
        filterset = BoardFilter(request.GET, request=request)
        self.assertEqual(filterset.qs.count(), 1)
        request.GET["before"] = ""

        request.user = user2
        filterset = BoardFilter(request.GET, request=request)
        self.assertEqual(filterset.qs.count(), 1)

    def test_board_filter_is_all_boards(self):
        user1 = User.objects.get(username="testuser1")
        request = self.factory.get(reverse("boards:board-list"))
        request.user = user1
        request.GET = request.GET.copy()
        request.GET["q"] = ""
        request.GET["after"] = ""
        request.GET["before"] = ""
        request.GET["owner"] = ""
        filterset = BoardFilter(request.GET, request=request, is_all_boards=True)
        self.assertEqual(filterset.qs.count(), 3)

        request.GET["q"] = "Test Board 1"
        filterset = BoardFilter(request.GET, request=request, is_all_boards=True)
        self.assertEqual(filterset.qs.count(), 1)
        request.GET["q"] = ""

        request.GET["before"] = date.today().strftime("%Y-%m-%d")
        filterset = BoardFilter(request.GET, request=request, is_all_boards=True)
        self.assertEqual(filterset.qs.count(), 1)
        request.GET["before"] = ""

        request.GET["owner"] = "testuser2"
        filterset = BoardFilter(request.GET, request=request, is_all_boards=True)
        self.assertEqual(filterset.qs.count(), 1)

        request.GET["owner"] = "testuser1,testuser2"
        filterset = BoardFilter(request.GET, request=request, is_all_boards=True)
        self.assertEqual(filterset.qs.count(), 3)
