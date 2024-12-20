import shutil
import tempfile
from pathlib import Path

import pytest
from pytest_factoryboy import register

from accounts.tests.factories import UserFactory
from boards.tests.factories import (
    AdditionalDataFactory,
    BgImageFactory,
    BoardFactory,
    ChemdoodleDataFactory,
    ExportFactory,
    ImageFactory,
    JSONDataFactory,
    MiscDataFactory,
    PostFactory,
    PostImageFactory,
    ReactionFactory,
    TopicFactory,
)
from jotlet.tests.factories import JSONFactory, JSONStringFactory


# Autouse Fixtures
@pytest.fixture(autouse=True)
def _enable_db_access_for_all_tests(db):
    pass


@pytest.fixture(scope="session")
def temp_dir():
    tmp_dir = tempfile.mkdtemp(prefix="jotlet_test_")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def _global_settings_override(settings, temp_dir):
    settings.MEDIA_ROOT = Path(temp_dir) / "media"
    settings.STATIC_ROOT = Path(temp_dir) / "static"


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

register(JSONDataFactory, "json_data")

register(MiscDataFactory, "misc_data")

register(ChemdoodleDataFactory, "chemdoodle_data")

register(ExportFactory, "export")

register(ImageFactory, "image")

register(PostImageFactory, "post_image")

register(BgImageFactory, "bg_image")

# Utility Factories
register(JSONFactory, "json_object")

register(JSONStringFactory, "json_string")
