from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_lazy_fixtures import lf

from boards.models import Export


class TestExportView:
    @pytest.mark.parametrize(
        ("test_user", "expected_response"),
        [
            (None, HTTPStatus.FOUND),
            (lf("user"), HTTPStatus.OK),
            (lf("user2"), HTTPStatus.FORBIDDEN),
            (lf("user3"), HTTPStatus.FORBIDDEN),
            (lf("user_staff"), HTTPStatus.OK),
        ],
    )
    def test_permissions(self, client, board, test_user, expected_response):
        if test_user:
            client.force_login(test_user)
        response = client.get(reverse("boards:board-export", kwargs={"slug": board.slug}))
        assert response.status_code == expected_response


class TestExportTablePartialView:
    @pytest.mark.parametrize(
        ("test_user", "expected_response"),
        [
            (None, HTTPStatus.FOUND),
            (lf("user"), HTTPStatus.OK),
            (lf("user2"), HTTPStatus.FORBIDDEN),
            (lf("user3"), HTTPStatus.FORBIDDEN),
            (lf("user_staff"), HTTPStatus.OK),
        ],
    )
    def test_permissions(self, client, board, test_user, expected_response):
        if test_user:
            client.force_login(test_user)
        response = client.get(reverse("boards:board-export-table", kwargs={"slug": board.slug}))
        assert response.status_code == expected_response


class TestExportCreateView:
    @pytest.fixture()
    def create_url(self, board):
        return reverse("boards:board-export-create", kwargs={"slug": board.slug})

    @pytest.mark.parametrize(
        ("test_user", "expected_response"),
        [
            (None, HTTPStatus.FOUND),
            (lf("user"), HTTPStatus.OK),
            (lf("user2"), HTTPStatus.FORBIDDEN),
            (lf("user3"), HTTPStatus.FORBIDDEN),
            (lf("user_staff"), HTTPStatus.OK),
        ],
    )
    def test_permissions(self, client, test_user, board, expected_response, create_url):
        if test_user:
            client.force_login(test_user)
        export_qs = Export.objects.filter(board__slug=board.slug)
        assert export_qs.count() == 0

        response = client.post(create_url)
        assert response.status_code == expected_response
        if expected_response == HTTPStatus.OK:
            assert export_qs.count() == 1
        else:
            assert export_qs.count() == 0

    @pytest.mark.parametrize("test_user", [lf("user"), lf("user_staff")])
    def test_get(self, client, test_user, create_url):
        if test_user:
            client.force_login(test_user)
        response = client.get(create_url)
        assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


class TestExportDeleteView:
    @pytest.fixture()
    def delete_url(self, export, delete_all):
        name = f"boards:board-export-delete{'-all' if delete_all else ''}"
        kwargs = {"slug": export.board.slug}
        if not delete_all:
            kwargs["pk"] = export.pk
        return reverse(name, kwargs=kwargs)

    @pytest.mark.parametrize(
        ("test_user", "expected_response"),
        [
            (None, HTTPStatus.FOUND),
            (lf("user"), HTTPStatus.OK),
            (lf("user2"), HTTPStatus.FORBIDDEN),
            (lf("user3"), HTTPStatus.FORBIDDEN),
            (lf("user_staff"), HTTPStatus.OK),
        ],
    )
    @pytest.mark.parametrize("delete_all", [True, False])
    @pytest.mark.parametrize("export_batch", [1, 3])
    def test_permissions(
        self, client, test_user, board, export_factory, expected_response, delete_all, export_batch, delete_url
    ):
        if test_user:
            client.force_login(test_user)

        export_factory.create_batch(export_batch, board=board)
        exports = Export.objects.filter(board=board)
        export_count = exports.count()

        response = client.post(delete_url)
        assert response.status_code == expected_response
        if expected_response == HTTPStatus.OK:
            assert exports.count() == (0 if delete_all else export_count - 1)
        else:
            assert exports.count() == export_count

    @pytest.mark.parametrize("test_user", [lf("user"), lf("user_staff")])
    @pytest.mark.parametrize("delete_all", [True, False])
    def test_get(self, client, test_user, delete_url):
        if test_user:
            client.force_login(test_user)
        response = client.get(delete_url)
        assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


class TestExportDownloadView:
    @pytest.fixture()
    def download_url(self, export):
        return reverse("boards:board-export-download", kwargs={"slug": export.board.slug, "pk": export.pk})

    @pytest.mark.parametrize(
        ("test_user", "expected_response"),
        [
            (None, HTTPStatus.FOUND),
            (lf("user"), HTTPStatus.OK),
            (lf("user2"), HTTPStatus.FORBIDDEN),
            (lf("user3"), HTTPStatus.FORBIDDEN),
            (lf("user_staff"), HTTPStatus.OK),
        ],
    )
    def test_permissions(self, client, test_user, download_url, expected_response):
        if test_user:
            client.force_login(test_user)
        response = client.get(download_url)
        assert response.status_code == expected_response

    @pytest.mark.parametrize("test_user", [lf("user"), lf("user_staff")])
    def test_get(self, client, test_user, download_url, export):
        client.force_login(test_user)
        response = client.get(download_url)
        assert response.status_code == HTTPStatus.OK
        assert response["HX-Redirect"] == export.file.url
