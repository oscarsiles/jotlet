import pytest
from freezegun import freeze_time

from boards.models import Export
from boards.tasks import export_cleanup
from jotlet.utils import offset_date


class TestTasks:
    @pytest.mark.parametrize(
        ("exports_count", "days_offset", "expected_count"),
        [
            (5, -7, 5),
            (5, -8, 0),
        ],
    )
    def test_export_cleanup(self, export_factory, exports_count, days_offset, expected_count):
        with freeze_time(offset_date(days=days_offset)):
            export_factory.create_batch(exports_count)
        export_cleanup()
        assert Export.objects.count() == expected_count
