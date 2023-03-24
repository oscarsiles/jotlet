from django.templatetags.static import static
from django.views import generic

from jotlet.utils import generate_link_header


class JotletLinkHeaderMixin(generic.View):
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.htmx:
            files_css = [
                static("css/vendor/bootstrap-5.3.0-alpha2.min.css"),
                static("css/vendor/bootstrap-icons-1.10.3.min.css"),
                static("css/styles.css"),
            ]
            files_fonts = [
                static("css/vendor/fonts/bootstrap-icons.woff2?8d200481aa7f02a2d63a331fc782cfaf"),
            ]
            files_scripts = [
                static("js/color-mode-toggler.js"),
                static("js/vendor/bootstrap-5.3.0-alpha2.bundle.min.js"),
                static("js/vendor/htmx-1.8.5.min.js"),
                static("js/base.js"),
                static("js/vendor/htmx-alpine-morph-1.8.5.min.js"),
                static("js/vendor/alpinejs-collapse-3.11.1.min.js"),
                static("js/vendor/alpinejs-mask-3.11.1.min.js"),
                static("js/vendor/alpinejs-morph-3.11.1.min.js"),
                static("js/vendor/alpinejs-persist-3.11.1.min.js"),
                static("js/vendor/alpinejs-3.11.1.min.js"),
            ]
            response = generate_link_header(response, files_css, files_scripts, files_fonts)
        return response
