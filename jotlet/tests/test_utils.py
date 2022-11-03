from django.http import HttpResponse

from jotlet.utils import generate_link_header


class TestGetLinkHeader:
    def test_files_css(self, blank_response):
        test_file1 = "file1.css"
        test_file2 = "/folder/file2.css"
        files_css = [test_file1, test_file2]
        link_header = generate_link_header(blank_response, files_css=files_css).get("Link")
        assert link_header == "<{}>; rel=preload; as=style, <{}>; rel=preload; as=style, ".format(*files_css)

    def test_files_font(self, blank_response):
        test_file1 = "file1.woff"
        test_file2 = "/folder/file2.ttf"
        files_font = [test_file1, test_file2]
        link_header = generate_link_header(blank_response, files_font=files_font).get("Link")
        # fmt: off
        assert link_header == \
            "<{}>; rel=preload; as=font; crossorigin=anonymous, <{}>; rel=preload; as=font; crossorigin=anonymous, ".format(*files_font)  # noqa: E501
        # fmt: on

    def test_files_js(self, blank_response):
        test_file1 = "file1.js"
        test_file2 = "/folder/file2.js"
        files_scripts = [test_file1, test_file2]
        link_header = generate_link_header(blank_response, files_scripts=files_scripts).get("Link")
        assert link_header == "<{}>; rel=preload; as=script, <{}>; rel=preload; as=script, ".format(*files_scripts)

    def test_domain_preconnect(self, blank_response):
        test_domain1 = "https://example.com"
        test_domain2 = "https://example.org"
        domain_preconnect = [test_domain1, test_domain2]
        link_header = generate_link_header(blank_response, domain_preconnect=domain_preconnect).get("Link")
        assert link_header == "<{}>; rel=preconnect, <{}>; rel=preconnect, ".format(*domain_preconnect)

    def test_link_header_appending(self, blank_response):
        response = generate_link_header(blank_response, files_css=["file1.css"])
        link_header1 = response.get("Link")
        response = generate_link_header(response, files_font=["file1.woff"])
        link_header2 = generate_link_header(HttpResponse(""), files_font=["file1.woff"]).get("Link")
        assert link_header1 + link_header2 == response.get("Link")
