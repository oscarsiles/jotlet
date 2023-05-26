import pytest
from pytest_factoryboy import register

from accounts.tests.factories import UserFactory
from boards.tests.factories import (
    AdditionalDataFactory,
    BgImageFactory,
    BoardFactory,
    ChemdoodleDataFactory,
    ImageFactory,
    MiscDataFactory,
    PostFactory,
    PostImageFactory,
    ReactionFactory,
    TopicFactory,
)
from jotlet.tests.factories import JSONFactory


# Autouse Fixtures
@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):  # pylint: disable=W0613, C0103
    pass


# Other Fixtures


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

register(AdditionalDataFactory, "additional_data")

register(MiscDataFactory, "misc_data")

register(ChemdoodleDataFactory, "chemdoodle_data")

register(ImageFactory, "image")

register(PostImageFactory, "post_image")

register(BgImageFactory, "bg_image")

# Utility Factories
register(JSONFactory, "json_data")
