from datetime import date, timedelta

from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import UserFactory
from boards.filters import BoardFilter
from boards.tests.factories import BoardFactory


# TODO: Implement full set of tests for all board_list_types
class BoardFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = UserFactory()
        cls.user2 = UserFactory()
        yesterday = timezone.now() - timedelta(days=1)
        board1 = BoardFactory(owner=cls.user1)
        board1.created_at = yesterday
        board1.save()
        BoardFactory(description="Some other text", owner=cls.user1)
        BoardFactory(description="Some other text", owner=cls.user2)

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_board_filter(self):
        board_list_type = "own"
        request = self.factory.get(reverse("boards:board-list", kwargs={"board_list_type": board_list_type}))
        request.user = self.user1
        request.GET = request.GET.copy()
        request.GET["q"] = ""
        request.GET["after"] = ""
        request.GET["before"] = ""
        request.GET["owner"] = self.user2.username
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 2)

        request.GET["q"] = "board"
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 2)
        request.GET["q"] = "description"
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 1)
        request.GET["q"] = ""

        request.GET["before"] = date.today().strftime("%Y-%m-%d")
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 1)
        request.GET["before"] = ""

        request.user = self.user2
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 1)

    def test_board_filter_is_all_boards(self):
        board_list_type = "all"
        request = self.factory.get(reverse("boards:board-list", kwargs={"board_list_type": board_list_type}))
        request.user = self.user1
        request.GET = request.GET.copy()
        request.GET["q"] = ""
        request.GET["after"] = ""
        request.GET["before"] = ""
        request.GET["owner"] = ""
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 3)

        request.GET["q"] = "Test Board 1"
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 1)
        request.GET["q"] = ""

        request.GET["before"] = date.today().strftime("%Y-%m-%d")
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 1)
        request.GET["before"] = ""

        request.GET["owner"] = ""
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 3)

        request.GET["owner"] = self.user2.username
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 1)
        request.GET["owner"] = self.user2.username.upper()  # case insensitive
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 1)

        request.GET["owner"] = ",".join([self.user1.username, self.user2.username])
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 3)
        request.GET["owner"] = ",".join([self.user1.username.title(), self.user2.username.upper()])
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        self.assertEqual(filterset.qs.count(), 3)
