from django.templatetags.static import static
from django.views import generic

from jotlet.utils import generate_link_header


class JotletLinkHeaderMixin(generic.View):
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.htmx:
            files_css = [
                static("vendor/bootstrap-5.3.0/css/bootstrap.min.css"),
                static("vendor/bootstrap-icons-1.10.5/bootstrap-icons.min.css"),
                static("css/styles.css"),
            ]
            files_fonts = [
                static("css/vendor/fonts/bootstrap-icons.woff2?8d200481aa7f02a2d63a331fc782cfaf"),
            ]
            files_scripts = [
                static("js/color-mode-toggler.js"),
                static("vendor/bootstrap-5.3.0/js/bootstrap.bundle.min.js"),
                static("vendor/htmx-1.9.2/htmx.min.js"),
                static("js/base.js"),
                static("vendor/htmx-1.9.2/htmx-alpine-morph.js"),
                static("vendor/alpinejs-3.12.1/alpinejs-collapse.min.js"),
                static("vendor/alpinejs-3.12.1/alpinejs-mask.min.js"),
                static("vendor/alpinejs-3.12.1/alpinejs-morph.min.js"),
                static("vendor/alpinejs-3.12.1/alpinejs-persist.min.js"),
                static("vendor/alpinejs-3.12.1/alpinejs.min.js"),
            ]
            response = generate_link_header(response, files_css, files_scripts, files_fonts)
        return response
