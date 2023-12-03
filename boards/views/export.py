from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count
from django.http import HttpResponse
from django.template.defaultfilters import pluralize
from django.urls import reverse_lazy
from django.views import generic
from django_htmx.http import HttpResponseClientRedirect, trigger_client_event

from boards.models import Board, Export


class ExportView(UserPassesTestMixin, generic.TemplateView):
    template_name = "boards/components/export.html"
    board: Board | None = None

    def test_func(self):
        self.board = (
            Board.objects.prefetch_related("owner")
            .prefetch_related("preferences")
            .prefetch_related("preferences__moderators")
            .get(slug=self.kwargs["slug"])
        )
        return self.board.is_export_allowed(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["board"] = self.board
        return context


class ExportTablePartialView(UserPassesTestMixin, generic.TemplateView):
    template_name = "boards/components/partials/export_table.html"
    board: Board | None = None

    def test_func(self):
        self.board = (
            Board.objects.prefetch_related("owner")
            .prefetch_related("preferences")
            .prefetch_related("preferences__moderators")
            .prefetch_related("exports")
            .annotate(num_exports=Count("exports"))
            .get(slug=self.kwargs["slug"])
        )
        return self.board.is_export_allowed(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["board"] = self.board
        context["exports"] = self.board.exports.all()
        return context


class ExportCreateView(UserPassesTestMixin, generic.View):
    model = Board
    board: Board | None = None
    http_method_names = ["post"]

    def test_func(self):
        self.board = (
            Board.objects.prefetch_related("owner")
            .prefetch_related("preferences")
            .prefetch_related("preferences__moderators")
            .get(slug=self.kwargs["slug"])
        )
        return self.board.is_export_allowed(self.request)

    def post(self, *args, **kwargs):
        Export.objects.create(board=self.board)

        return trigger_client_event(
            trigger_client_event(
                HttpResponse(),
                "showMessage",
                {
                    "message": "Export Created",
                    "color": "success",
                },
            ),
            "exportCreated",
            None,
        )


class ExportDeleteView(UserPassesTestMixin, generic.View):
    model = Board
    board: Board | None = None
    http_method_names = ["post"]

    def test_func(self):
        self.board = (
            Board.objects.prefetch_related("owner")
            .prefetch_related("preferences")
            .prefetch_related("preferences__moderators")
            .get(slug=self.kwargs["slug"])
        )
        return self.board.is_export_allowed(self.request)

    def post(self, request, *args, **kwargs):
        if request.path == reverse_lazy("boards:board-export-delete-all", kwargs={"slug": self.board.slug}):
            count = self.board.exports.all().count()
            self.board.exports.all().delete()
            message = f"{count} Export{pluralize(count)} Deleted"
        else:
            message = "Export Deleted"
            Export.objects.get(pk=self.kwargs["pk"]).delete()

        return trigger_client_event(
            trigger_client_event(
                HttpResponse(),
                "showMessage",
                {
                    "message": message,
                    "color": "danger",
                },
            ),
            "exportDeleted",
            None,
        )


class ExportDownloadView(UserPassesTestMixin, generic.View):
    model = Board
    board: Board | None = None

    def test_func(self):
        self.board = (
            Board.objects.prefetch_related("owner")
            .prefetch_related("preferences")
            .prefetch_related("preferences__moderators")
            .get(slug=self.kwargs["slug"])
        )
        return self.board.is_export_allowed(self.request)

    def get(self, *args, **kwargs):
        export = Export.objects.get(pk=self.kwargs["pk"])
        return trigger_client_event(HttpResponseClientRedirect(export.file.url), "exportDownloaded", None)
