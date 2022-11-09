from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic

from boards.filters import BoardFilter
from boards.forms import SearchBoardsForm
from boards.mixins import BoardListLinkHeaderMixin, PaginatedFilterViewsMixin
from boards.models import Board
from jotlet.mixins.headers import JotletLinkHeaderMixin


class IndexView(JotletLinkHeaderMixin, BoardListLinkHeaderMixin, generic.FormView):
    model = Board
    template_name = "boards/index.html"
    form_class = SearchBoardsForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()
        elif self.request.user.is_authenticated:
            context["board_list_type"] = "own"
        return context

    def form_valid(self, form):
        return HttpResponseRedirect(reverse("boards:board", kwargs={"slug": form.cleaned_data["board_slug"]}))


class IndexAllBoardsView(
    JotletLinkHeaderMixin, BoardListLinkHeaderMixin, LoginRequiredMixin, UserPassesTestMixin, generic.TemplateView
):
    model = Board
    template_name = "boards/index.html"
    permission_required = "boards.can_view_all_boards"

    def test_func(self):
        return self.request.user.has_perm(self.permission_required) or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["board_list_type"] = "all"
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
            self.request.user.profile.boards_paginate_by = int(page_size)
            self.request.user.profile.save()
        self.paginate_by = self.request.user.profile.boards_paginate_by
        context = super().get_context_data(**kwargs)

        paginator = Paginator(self.object_list, self.paginate_by)
        page_range = paginator.get_elided_page_range(number=page, on_each_side=1, on_ends=1)

        context["filter"] = self.filterset
        context["page_range"] = page_range
        context["paginate_by"] = self.paginate_by
        context["pagination_sizes"] = [5, 10, 20, 50]
        context["board_list_type"] = self.board_list_type
        return context
