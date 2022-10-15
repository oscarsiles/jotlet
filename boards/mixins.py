from django.templatetags.static import static
from django.views import generic

from jotlet.utils import generate_link_header


class BoardListLinkHeaderMixin(generic.View):
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        try:
            if not request.htmx:
                board_list_type = response.context_data.get("board_list_type", "")
                files_css = []
                files_js = [
                    static("boards/js/index.js"),
                ]
                if request.user.is_authenticated:
                    files_js += [static("boards/js/components/board_list.js")]

                if board_list_type in ["all", "mod"]:
                    files_css += [
                        static("css/3rdparty/tagify-4.16.4.min.css"),
                    ]
                    files_js += [
                        static("js/3rdparty/tagify-4.16.4.min.js"),
                        static("js/3rdparty/tagify-4.16.4.polyfills.min.js"),
                    ]

                response = generate_link_header(response, files_css, files_js)
        except Exception as e:
            raise e
        finally:
            return response


class PaginatedFilterViewsMixin(generic.View):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET:
            querystring = self.request.GET.copy()
            if self.request.GET.get("page"):
                del querystring["page"]
            context["querystring"] = querystring.urlencode()
        return context
