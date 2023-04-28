from django.templatetags.static import static
from django.views import generic

from jotlet.utils import generate_link_header


class JotletLinkHeaderMixin(generic.View):
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.htmx:
            files_css = [
                static("css/vendor/bootstrap-5.3.0-alpha3.min.css"),
                static("css/vendor/bootstrap-icons-1.10.5.min.css"),
                static("css/styles.css"),
            ]
            files_fonts = [
                static("css/vendor/fonts/bootstrap-icons.woff2?8d200481aa7f02a2d63a331fc782cfaf"),
            ]
            files_scripts = [
                static("js/color-mode-toggler.js"),
                static("js/vendor/bootstrap-5.3.0-alpha3.bundle.min.js"),
                static("js/vendor/htmx-1.9.1/htmx.min.js"),
                static("js/base.js"),
                static("js/vendor/htmx-1.9.1/htmx-alpine-morph.min.js"),
                static("js/vendor/alpinejs-3.12.0/alpinejs-collapse.min.js"),
                static("js/vendor/alpinejs-3.12.0/alpinejs-mask.min.js"),
                static("js/vendor/alpinejs-3.12.0/alpinejs-morph.min.js"),
                static("js/vendor/alpinejs-3.12.0/alpinejs-persist.min.js"),
                static("js/vendor/alpinejs-3.12.0/alpinejs.min.js"),
            ]
            response = generate_link_header(response, files_css, files_scripts, files_fonts)
        return response
