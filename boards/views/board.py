from urllib.parse import urlparse

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.templatetags.static import static
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.cache import cache_control
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh, trigger_client_event

from boards.forms import BoardPreferencesForm
from boards.models import Board, BoardPreferences, Image
from boards.utils import get_is_moderator
from jotlet.utils import generate_link_header


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        board = self.object

        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()

        if board.preferences.background_type == "i":
            context["bg_image"] = board.preferences.background_image

        context["topics"] = board.topics.order_by("-created_at")
        context["support_webp"] = self.request.META.get("HTTP_ACCEPT", "").find("image/webp") > -1
        context["is_moderator"] = get_is_moderator(self.request.user, board)
        return context

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.htmx:
            preferences = self.object.preferences
            files_css = [
                static("css/3rdparty/easymde-2.18.0.min.css"),
                static("boards/css/board.css"),
            ]
            files_js = [
                static("js/3rdparty/alpinejs-intersect-3.10.3.min.js"),
                static("js/3rdparty/marked-4.1.1.min.js"),
                static("js/3rdparty/purify-2.4.0.min.js"),
                static("js/3rdparty/easymde-2.18.0.min.js"),
                static("boards/js/3rdparty/robust-websocket.js"),
                static("boards/js/board.js"),
            ]
            files_fonts = []
            domain_preconnect = []

            if preferences.enable_latex:
                files_js += [
                    static("boards/js/components/board_mathjax.js"),
                    "https://polyfill.io/v3/polyfill.min.js?features=es6",
                ]
                files_fonts += [
                    "https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/output/chtml/fonts/woff-v2/MathJax_Zero.woff",
                    "https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/output/chtml/fonts/woff-v2/MathJax_Main-Regular.woff",  # noqa: E501
                    "https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/output/chtml/fonts/woff-v2/MathJax_Math-Italic.woff",  # noqa: E501
                ]
                domain_preconnect += ["https://cdn.jsdelivr.net"]

            if preferences.enable_identicons:
                files_js += [
                    static("js/3rdparty/jdenticon-3.2.0.min.js"),
                ]

            response = generate_link_header(response, files_css, files_js, files_fonts, domain_preconnect)

        return response


@method_decorator(cache_control(public=True), name="dispatch")
class BoardPreferencesView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = BoardPreferences
    board = None
    template_name = "boards/components/board_preferences.html"
    form_class = BoardPreferencesForm

    def test_func(self):
        self.board = board = Board.objects.prefetch_related("preferences__moderators").get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def get_object(self):  # needed to prevent 'slug' FieldError
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
    fields = ["title", "description"]
    template_name = "boards/board_form.html"
    permission_required = "boards.add_board"

    def test_func(self):
        return self.request.user.has_perm(self.permission_required) or self.request.user.is_staff

    def form_valid(self, form):
        board = form.save(commit=False)
        board.owner = self.request.user
        board.save()

        return HttpResponseClientRedirect(reverse_lazy("boards:board", kwargs={"slug": board.slug}))


class UpdateBoardView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = Board
    board = None
    fields = ["title", "description"]
    template_name = "boards/board_form.html"

    def test_func(self):
        board = self.get_object()
        return (
            self.request.user.has_perm("boards.change_board")
            or self.request.user == board.owner
            or self.request.user.is_staff
        )

    def get_object(self):
        if self.board is None:
            self.board = super().get_object()
        return self.board

    def form_valid(self, form):
        super().form_valid(form)

        return HttpResponseClientRefresh()


class DeleteBoardView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    model = Board
    board = None
    template_name = "boards/board_confirm_delete.html"
    success_url = reverse_lazy("boards:index")

    def test_func(self):
        board = self.get_object()
        return (
            self.request.user.has_perm("boards.delete_board")
            or self.request.user == board.owner
            or self.request.user.is_staff
        )

    def get_object(self):
        if self.board is None:
            self.board = super().get_object()
        return self.board


@method_decorator(cache_control(public=True), name="dispatch")
class ImageSelectView(LoginRequiredMixin, generic.TemplateView):
    template_name = "boards/components/image_select.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["images"] = Image.objects.filter(type=self.kwargs["type"])
        return context


class QrView(UserPassesTestMixin, generic.TemplateView):
    template_name = "boards/components/qr.html"

    def test_func(self):
        board = Board.objects.prefetch_related("preferences__moderators").get(slug=self.kwargs["slug"])
        return get_is_moderator(self.request.user, board)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = self.kwargs["slug"]
        context["url"] = self.request.build_absolute_uri(
            reverse_lazy("boards:board", kwargs={"slug": self.kwargs["slug"]})
        )
        return context
