import asyncio

import pytest
from django.http import HttpResponse
from pytest_factoryboy import register

from accounts.tests.factories import UserFactory
from boards.tests.factories import (
    BgImageFactory,
    BoardFactory,
    ImageFactory,
    PostFactory,
    PostImageFactory,
    ReactionFactory,
    TopicFactory,
)


# Autouse Fixtures
@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass


@pytest.fixture(autouse=True)
def override_test_settings(settings):
    settings.MAX_IMAGE_HEIGHT = 500
    settings.MAX_IMAGE_WIDTH = 500


# Other Fixtures
@pytest.fixture
def blank_response():
    return HttpResponse("")


@pytest.yield_fixture(scope="session")
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Factoryboy Fixtures
register(UserFactory, "user")
register(UserFactory, "user2")
register(UserFactory, "user3")
register(UserFactory, "user_staff", is_staff=True)
register(UserFactory, "user_superuser", is_staff=True, is_superuser=True)

register(BoardFactory, "board")

register(TopicFactory, "topic")

register(PostFactory, "post")

register(ReactionFactory, "reaction")

register(ImageFactory, "image")

register(PostImageFactory, "post_image")

register(BgImageFactory, "bg_image")
