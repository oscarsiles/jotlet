from django.templatetags.static import static

from jotlet.utils import generate_link_header


class HeadersMiddleware:
    whitelisted_urls = [
        "/boards/",
        "/accounts/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if any(x in request.path for x in self.whitelisted_urls):
            if not request.htmx:
                files_css = [
                    static("css/3rdparty/bootstrap-5.2.2.min.css"),
                    static("css/3rdparty/bootstrap-icons-1.9.1.min.css"),
                    static("css/styles.css"),
                ]
                files_fonts = [
                    static("css/3rdparty/fonts/bootstrap-icons.woff2?8d200481aa7f02a2d63a331fc782cfaf"),
                ]
                files_scripts = [
                    static("js/3rdparty/bootstrap-5.2.2.bundle.min.js"),
                    static("js/3rdparty/htmx-1.8.0.min.js"),
                    static("js/base.js"),
                    static("js/3rdparty/alpinejs-collapse-3.10.3.min.js"),
                    static("js/3rdparty/alpinejs-mask-3.10.3.min.js"),
                    static("js/3rdparty/alpinejs-morph-3.10.3.min.js"),
                    static("js/3rdparty/alpinejs-3.10.3.min.js"),
                ]
                response = generate_link_header(response, files_css, files_scripts, files_fonts)

        return response
