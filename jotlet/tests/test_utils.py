import pytest
from django.http import HttpResponse


@pytest.fixture
def blank_response():
    return HttpResponse("")
