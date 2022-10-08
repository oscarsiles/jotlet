from django.templatetags.static import static


class HeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
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
            link_header = response.get("Link", "")
            for file in files_css:
                link_header += f"<{file}>; rel=preload; as=style, "
            for file in files_fonts:
                link_header += f"<{file}>; rel=preload; as=font; crossorigin=anonymous, "
            for file in files_scripts:
                link_header += f"<{file}>; rel=preload; as=script, "

            response["Link"] = link_header

        return response
