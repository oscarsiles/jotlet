from urllib.parse import urlparse

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.cache import cache_control
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh, trigger_client_event

from boards.forms import BoardCreateForm, BoardPreferencesForm
from boards.models import Board, BoardPreferences, Image
from boards.utils import get_is_moderator


class BoardView(generic.DetailView):
    model = Board
    template_name = "boards/board_index.html"

    def get_template_names(self):
        template_names = super().get_template_names()
        if self.request.htmx.current_url:
            url = urlparse(self.request.htmx.current_url).path
            if url == reverse("boards:board", kwargs={"slug": self.kwargs["slug"]}):
                template_names[0] = "boards/components/board.html"

        return template_names

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related("owner")
            .prefetch_related("preferences")
            .prefetch_related("preferences__moderators")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        board = self.object

        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()

        if board.preferences.background_type == "i":
            context["bg_image"] = board.preferences.background_image

        context["topics"] = board.topics.order_by("created_at")
        context["support_webp"] = self.request.META.get("HTTP_ACCEPT", "").find("image/webp") > -1
        context["is_moderator"] = get_is_moderator(self.request.user, board)
        return context


@method_decorator(cache_control(public=True), name="dispatch")
class BoardPreferencesView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = BoardPreferences
    board: Board | None = None
    template_name = "boards/components/board_preferences.html"
    form_class = BoardPreferencesForm

    def test_func(self):
        self.board = board = (
            Board.objects.prefetch_related("owner")
            .prefetch_related("preferences")
            .prefetch_related("preferences__moderators")
            .get(slug=self.kwargs["slug"])
        )
        return self.request.user == board.owner or self.request.user.is_staff

    def get_object(self, queryset=None):  # needed to prevent 'slug' FieldError
        board = self.board
        if not BoardPreferences.objects.filter(board=board).exists():
            board.preferences = BoardPreferences.objects.create(board=board)
            board.preferences.save()
        return board.preferences

    def get_form_kwargs(self, **kwargs):
        kwargs = super().get_form_kwargs(**kwargs)
        kwargs["board"] = self.board
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        response.status_code = 204

        return trigger_client_event(
            trigger_client_event(
                response,
                "showMessage",
                {
                    "message": "Preferences Saved",
                    "color": "warning",
                },
            ),
            "preferencesChanged",
            None,
        )


class CreateBoardView(LoginRequiredMixin, UserPassesTestMixin, generic.CreateView):
    model = Board
    template_name = "boards/board_form.html"
    permission_required = "boards.add_board"
    form_class = BoardCreateForm

    def test_func(self):
        return self.request.user.has_perm(self.permission_required) or self.request.user.is_staff

    def form_valid(self, form):
        board = form.save(commit=False)
        board.owner = self.request.user
        board.save()

        return HttpResponseClientRedirect(reverse_lazy("boards:board", kwargs={"slug": board.slug}))


class UpdateBoardView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = Board
    board: Board | None = None
    template_name = "boards/board_form.html"
    form_class = BoardCreateForm

    def test_func(self):
        board = self.get_object()
        return (
            self.request.user.has_perm("boards.change_board")
            or self.request.user == board.owner
            or self.request.user.is_staff
        )

    def get_object(self, queryset=None):
        if self.board is None:
            self.board = super().get_object()
        return self.board

    def form_valid(self, form):
        super().form_valid(form)

        return HttpResponseClientRefresh()


class DeleteBoardView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    model = Board
    board: Board | None = None
    template_name = "boards/board_confirm_delete.html"
    success_url = reverse_lazy("boards:index")

    def test_func(self):
        board = self.get_object()
        return (
            self.request.user.has_perm("boards.delete_board")
            or self.request.user == board.owner
            or self.request.user.is_staff
        )

    def get_object(self, queryset=None):
        if self.board is None:
            self.board = super().get_object()
        return self.board


@method_decorator(cache_control(public=True), name="dispatch")
class ImageSelectView(LoginRequiredMixin, generic.TemplateView):
    template_name = "boards/components/image_select.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["images"] = Image.objects.filter(image_type=self.kwargs["image_type"])
        return context


class QrView(UserPassesTestMixin, generic.TemplateView):
    template_name = "boards/components/qr.html"
    board: Board | None = None

    def test_func(self):
        self.board = (
            Board.objects.prefetch_related("owner")
            .prefetch_related("preferences")
            .prefetch_related("preferences__moderators")
            .get(slug=self.kwargs["slug"])
        )
        return get_is_moderator(self.request.user, self.board)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["board"] = self.board
        context["url"] = self.request.build_absolute_uri(
            reverse_lazy("boards:board", kwargs={"slug": self.kwargs["slug"]})
        )
        return context
