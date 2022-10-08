from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.templatetags.static import static
from django.urls import reverse
from django.views import generic

from boards.filters import BoardFilter
from boards.forms import SearchBoardsForm
from boards.models import Board
from jotlet.utils import generate_link_header


class IndexViewLinkHeaderMixin(generic.View):
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.htmx:
            is_all_boards = response.context_data.get("board_list_type", "own") == "all"
            files_css = []
            files_js = [
                static("boards/js/index.js"),
            ]

            if is_all_boards:
                files_css += [
                    static("css/3rdparty/tagify-4.16.4.min.css"),
                ]
                files_js += [
                    static("js/3rdparty/tagify-4.16.4.min.js"),
                    static("js/3rdparty/tagify-4.16.4.polyfills.min.js"),
                ]

            response = generate_link_header(response, files_css, files_js)

        return response


class IndexView(IndexViewLinkHeaderMixin, generic.FormView):
    model = Board
    template_name = "boards/index.html"
    form_class = SearchBoardsForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()

        context["board_list_type"] = "own"
        return context

    def form_valid(self, form):
        return HttpResponseRedirect(reverse("boards:board", kwargs={"slug": form.cleaned_data["board_slug"]}))


class IndexAllBoardsView(IndexViewLinkHeaderMixin, LoginRequiredMixin, UserPassesTestMixin, generic.TemplateView):
    model = Board
    template_name = "boards/index.html"
    permission_required = "boards.can_view_all_boards"

    def test_func(self):
        return self.request.user.has_perm(self.permission_required) or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["board_list_type"] = "all"
        return context


class PaginatedFilterViewsMixin(generic.View):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET:
            querystring = self.request.GET.copy()
            if self.request.GET.get("page"):
                del querystring["page"]
            context["querystring"] = querystring.urlencode()
        return context


class BoardListView(LoginRequiredMixin, PaginatedFilterViewsMixin, generic.ListView):
    model = Board
    template_name = "boards/components/board_list.html"
    context_object_name = "boards"
    paginate_by = None
    board_list_type = "own"
    filterset = None

    def get_queryset(self):
        self.board_list_type = self.kwargs["board_list_type"]
        self.filterset = BoardFilter(self.request.GET, request=self.request, board_list_type=self.board_list_type)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        page = self.request.GET.get("page", 1)
        page_size = self.request.GET.get("paginate_by", None)
        if page_size:
            page_size = int(page_size)
            self.request.session["paginate_by"] = page_size
        self.paginate_by = self.request.session.get("paginate_by", 10)
        context = super().get_context_data(**kwargs)

        paginator = Paginator(self.object_list, self.paginate_by)
        page_range = paginator.get_elided_page_range(number=page, on_each_side=1, on_ends=1)

        context["filter"] = self.filterset
        context["page_range"] = page_range
        context["paginate_by"] = self.paginate_by
        context["pagination_sizes"] = [5, 10, 20, 50]
        context["board_list_type"] = self.board_list_type
        return context

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        files_css = []
        files_js = [
            static("boards/js/components/board_list.js"),
        ]

        response = generate_link_header(response, files_css, files_js)

        return response
