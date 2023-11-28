import datetime

import pytest
from django.urls import reverse
from freezegun import freeze_time

from boards.filters import BoardFilter
from jotlet.utils import offset_date


# TODO: Implement full set of tests for all board_list_types
class TestBoardFilter:
    @pytest.fixture(autouse=True)
    def _setup_method(self, user, user2, board_factory):
        board_factory.reset_sequence(1)
        with freeze_time(offset_date(days=-1)):
            board_factory(owner=user)
        board_factory(description="Some other text", owner=user)
        board_factory(description="Some other text", owner=user2)

    def test_board_filter(self, rf, user, user2):
        board_list_type = "own"
        request = rf.get(reverse("boards:board-list", kwargs={"board_list_type": board_list_type}))
        request.user = user
        request.GET = request.GET.copy()
        request.GET["q"] = ""
        request.GET["after"] = ""
        request.GET["before"] = ""
        request.GET["owner"] = user2.username
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 2  # noqa: PLR2004

        request.GET["q"] = "board"
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 2  # noqa: PLR2004
        request.GET["q"] = "description"
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 1
        request.GET["q"] = ""

        request.GET["before"] = datetime.datetime.now(tz=datetime.UTC).date().strftime("%Y-%m-%d")
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 1
        request.GET["before"] = ""

        request.user = user2
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 1

    def test_board_filter_is_all_boards(self, rf, user, user2):
        board_list_type = "all"
        request = rf.get(reverse("boards:board-list", kwargs={"board_list_type": board_list_type}))
        request.user = user
        request.GET = request.GET.copy()
        request.GET["q"] = ""
        request.GET["after"] = ""
        request.GET["before"] = ""
        request.GET["owner"] = ""
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 3  # noqa: PLR2004

        request.GET["q"] = "Test Board 1"
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 1
        request.GET["q"] = ""

        request.GET["before"] = datetime.datetime.now(tz=datetime.UTC).date().strftime("%Y-%m-%d")
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 1
        request.GET["before"] = ""

        request.GET["owner"] = ""
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 3  # noqa: PLR2004

        request.GET["owner"] = user2.username
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 1
        request.GET["owner"] = user2.username.upper()  # case insensitive
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 1

        request.GET["owner"] = f"{user.username},{user2.username}"
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 3  # noqa: PLR2004
        request.GET["owner"] = f"{user.username.title()},{user2.username.upper()}"
        filterset = BoardFilter(request.GET, request=request, board_list_type=board_list_type)
        assert filterset.qs.count() == 3  # noqa: PLR2004
