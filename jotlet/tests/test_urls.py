from http import HTTPStatus


class TestRobots:
    # from Adam Johnson's blog
    def test_get(self, client):
        response = client.get("/robots.txt")

        assert response.status_code == HTTPStatus.OK
        assert response["content-type"] == "text/plain"
        lines = response.content.decode().splitlines()
        assert lines[0] == "User-Agent: *"

    def test_post_disallowed(self, client):
        response = client.post("/robots.txt")

        assert HTTPStatus.METHOD_NOT_ALLOWED == response.status_code
