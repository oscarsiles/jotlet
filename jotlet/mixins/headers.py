from django.templatetags.static import static
from django.views import generic

from jotlet.utils import generate_link_header


class JotletLinkHeaderMixin(generic.View):
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.htmx:
            files_css = [
                static("css/3rdparty/bootstrap-5.2.2.min.css"),
                static("css/3rdparty/bootstrap-icons-1.10.1.min.css"),
                static("css/styles.css"),
            ]
            files_fonts = [
                static("css/3rdparty/fonts/bootstrap-icons.woff2?8d200481aa7f02a2d63a331fc782cfaf"),
            ]
            files_scripts = [
                static("js/3rdparty/bootstrap-5.2.2.bundle.min.js"),
                static("js/3rdparty/htmx-1.8.4.min.js"),
                static("js/base.js"),
                static("js/3rdparty/htmx-alpine-morph-1.8.4.min.js"),
                static("js/3rdparty/alpinejs-collapse-3.10.4.min.js"),
                static("js/3rdparty/alpinejs-mask-3.10.4.min.js"),
                static("js/3rdparty/alpinejs-morph-3.10.4.min.js"),
                static("js/3rdparty/alpinejs-3.10.4.min.js"),
            ]
            response = generate_link_header(response, files_css, files_scripts, files_fonts)
        return response
