from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views import generic
from django_htmx.http import trigger_client_event

from boards.models import Board, Topic
from boards.utils import get_is_moderator


class CreateTopicView(LoginRequiredMixin, UserPassesTestMixin, generic.CreateView):
    model = Topic
    fields = ["subject", "locked"]
    template_name = "boards/topic_form.html"

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def form_valid(self, form):
        form.instance.board_id = Board.objects.get(slug=self.kwargs["slug"]).id
        response = super().form_valid(form)
        response.status_code = 204

        return trigger_client_event(
            trigger_client_event(
                response,
                "showMessage",
                {
                    "message": "Topic Created",
                    "color": "success",
                },
            ),
            "topicCreated",
            None,
        )


class UpdateTopicView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = Topic
    fields = ["subject", "locked"]
    template_name = "boards/topic_form.html"

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def form_valid(self, form):
        response = super().form_valid(form)
        response.status_code = 204

        return trigger_client_event(
            trigger_client_event(
                response,
                "showMessage",
                {
                    "message": f'Topic "{self.object.subject}" updated',
                },
            ),
            "topicUpdated",
            None,
        )


class DeleteTopicView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    model = Topic
    template_name = "boards/topic_confirm_delete.html"

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def form_valid(self, form):
        topic_subject = self.object.subject
        response = super().form_valid(form)
        response.status_code = 204

        return trigger_client_event(
            trigger_client_event(
                response,
                "showMessage",
                {
                    "message": f'Topic "{topic_subject}" Deleted',
                    "color": "danger",
                },
            ),
            "topicDeleted",
            None,
        )

    def get_success_url(self):
        return reverse_lazy("boards:board", kwargs={"slug": self.kwargs["slug"]})


class TopicFetchView(generic.TemplateView):
    template_name = "boards/components/topic.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["board"] = board = (
            Board.objects.select_related("owner")
            .select_related("preferences")
            .prefetch_related("preferences__moderators")
            .get(slug=self.kwargs["slug"])
        )
        context["topic"] = board.topics.get(pk=self.kwargs["pk"])
        context["is_moderator"] = get_is_moderator(self.request.user, board)
        return context


class TopicLockView(UserPassesTestMixin, generic.View):
    http_method_names = ["post"]
    permission_required = "boards.lock_board"

    def test_func(self):
        return self.request.user.has_perm(self.permission_required) or self.request.user.is_staff
