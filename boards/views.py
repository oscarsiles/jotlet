from asgiref.sync import async_to_sync
from random import randint

from channels.layers import get_channel_layer
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.cache import cache_control

from django_htmx.http import HttpResponseClientRefresh

from .forms import BoardPreferencesForm, SearchBoardsForm
from .models import Board, BoardPreferences, Image, Topic, Post


def channel_group_send(group_name, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name, message)


class IndexView(generic.FormView):
    model = Board
    template_name = "boards/index.html"
    form_class = SearchBoardsForm

    def form_valid(self, form):
        self.form = form
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context["form"] = self.get_form()
        if self.request.user.is_staff:
            context["all_boards"] = Board.objects.all()
        return context

    def get_success_url(self):
        return reverse("boards:board", kwargs={"slug": self.form.cleaned_data["board_slug"]})


class BoardView(generic.DetailView):
    model = Board
    template_name = "boards/board_index.html"

    def get_context_data(self, **kwargs):
        context = super(BoardView, self).get_context_data(**kwargs)
        context["topics"] = Topic.objects.filter(board=self.object)
        context["random_int"] = randint(0, 999999)

        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()
        return context


@method_decorator(cache_control(public=True), name="dispatch")
class BoardPreferencesView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = BoardPreferences
    template_name = "boards/board_preferences.html"
    form_class = BoardPreferencesForm

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def get_object(self):  # needed to prevent 'slug' FieldError
        board = Board.objects.get(slug=self.kwargs["slug"])
        if not BoardPreferences.objects.filter(board=board).exists():
            board.preferences = BoardPreferences.objects.create(board=board)
            BoardPreferences.save(board.preferences)
        return board.preferences

    def get_form_kwargs(self, **kwargs):
        kwargs = super(BoardPreferencesView, self).get_form_kwargs(**kwargs)
        kwargs["slug"] = self.kwargs["slug"]
        return kwargs

    def form_valid(self, form):
        super(BoardPreferencesView, self).form_valid(form)
        channel_group_send(
            f"board_{self.kwargs.get('slug')}",
            {
                "type": "board_preferences_changed",
            },
        )
        return HttpResponseClientRefresh()


class CreateBoardView(LoginRequiredMixin, UserPassesTestMixin, generic.CreateView):
    model = Board
    fields = ["title", "description"]
    template_name = "boards/board_form.html"

    def test_func(self):
        return self.request.user.has_perm("boards.add_board") or self.request.user.is_staff

    def form_valid(self, form):
        board = form.save(commit=False)
        board.owner = self.request.user
        board.save()
        return super(CreateBoardView, self).form_valid(form)


class UpdateBoardView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = Board
    fields = ["title", "description"]
    template_name = "boards/board_form.html"

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return (
            self.request.user.has_perm("boards.change_board")
            or self.request.user == board.owner
            or self.request.user.is_staff
        )


class DeleteBoardView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    model = Board
    template_name = "boards/board_confirm_delete.html"
    success_url = reverse_lazy("boards:index")

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return (
            self.request.user.has_perm("boards.delete_board")
            or self.request.user == board.owner
            or self.request.user.is_staff
        )


class CreateTopicView(LoginRequiredMixin, UserPassesTestMixin, generic.CreateView):
    model = Topic
    fields = ["subject"]
    template_name = "boards/topic_form.html"

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def form_valid(self, form):
        form.instance.board_id = Board.objects.get(slug=self.kwargs["slug"]).id
        super(CreateTopicView, self).form_valid(form)
        channel_group_send(
            f"board_{self.kwargs.get('slug')}",
            {
                "type": "topic_created",
                "topic_pk": self.object.pk,
            },
        )
        return HttpResponse("")


class UpdateTopicView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = Topic
    fields = ["subject"]
    template_name = "boards/topic_form.html"

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def form_valid(self, form):
        super(UpdateTopicView, self).form_valid(form)
        channel_group_send(
            f"board_{self.kwargs.get('slug')}",
            {
                "type": "topic_updated",
                "topic_pk": self.object.pk,
            },
        )
        return HttpResponse("")


class DeleteTopicView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    model = Topic
    template_name = "boards/topic_confirm_delete.html"

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def get_success_url(self):
        channel_group_send(
            f"board_{self.kwargs.get('slug')}",
            {
                "type": "topic_deleted",
                "topic_pk": self.object.pk,
            },
        )
        return reverse_lazy("boards:board", kwargs={"slug": self.kwargs["slug"]})


class CreatePostView(generic.CreateView):
    model = Post
    fields = ["content"]
    template_name = "boards/post_form.html"

    def form_valid(self, form):
        form.instance.topic_id = self.kwargs.get("topic_pk")
        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()
        form.instance.session_key = self.request.session.session_key
        if form.instance.topic.board.preferences.require_approval:
            form.instance.approved = (
                self.request.user.has_perm("boards.can_approve_posts")
                or self.request.user in form.instance.topic.board.preferences.moderators.all()
                or self.request.user == form.instance.topic.board.owner
                or self.request.user.is_staff
            )

        super(CreatePostView, self).form_valid(form)

        channel_group_send(
            f"board_{self.kwargs.get('slug')}",
            {
                "type": "post_created",
                "topic_pk": self.kwargs.get("topic_pk"),
            },
        )
        return HttpResponse("")


class UpdatePostView(UserPassesTestMixin, generic.UpdateView):
    model = Post
    fields = ["content"]
    template_name = "boards/post_form.html"

    def test_func(self):
        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()
        post = Post.objects.get(pk=self.kwargs["pk"])
        return (
            self.request.session.session_key == post.session_key
            or self.request.user.has_perm("boards.change_post")
            or self.request.user in post.topic.board.preferences.moderators.all()
            or self.request.user == post.topic.board.owner
            or self.request.user.is_staff
        )

    def form_valid(self, form):
        super(UpdatePostView, self).form_valid(form)
        channel_group_send(
            f"board_{self.kwargs.get('slug')}",
            {
                "type": "post_updated",
                "post_pk": self.object.pk,
            },
        )
        return HttpResponse("")


class DeletePostView(UserPassesTestMixin, generic.DeleteView):
    model = Post
    template_name = "boards/post_confirm_delete.html"

    def test_func(self):
        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()
        post = Post.objects.get(pk=self.kwargs["pk"])
        return (
            self.request.session.session_key == post.session_key
            or self.request.user.has_perm("boards.delete_post")
            or self.request.user in post.topic.board.preferences.moderators.all()
            or self.request.user == post.topic.board.owner
            or self.request.user.is_staff
        )

    def get_success_url(self):
        channel_group_send(
            f"board_{self.kwargs.get('slug')}",
            {
                "type": "post_deleted",
                "post_pk": self.object.pk,
            },
        )
        return reverse_lazy(
            "boards:board", kwargs={"slug": self.object.topic.board.slug, "slug": self.kwargs["slug"]}
        )


# HTMX Stuff


class BoardFetchView(generic.TemplateView):
    template_name = "boards/components/board.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["board"] = Board.objects.get(slug=self.kwargs["slug"])
        return context


class TopicFetchView(generic.TemplateView):
    template_name = "boards/components/topic.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["topic"] = Topic.objects.get(pk=self.kwargs["pk"])
        return context


class PostFetchView(generic.TemplateView):
    template_name = "boards/components/post.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["post"] = Post.objects.get(pk=self.kwargs["pk"])
        return context


class PostToggleApprovalView(LoginRequiredMixin, UserPassesTestMixin, generic.View):
    def test_func(self):
        post = Post.objects.get(pk=self.kwargs["pk"])
        return (
            self.request.user.has_perm("boards.can_approve_posts")
            or self.request.user in post.topic.board.preferences.moderators.all()
            or self.request.user == post.topic.board.owner
            or self.request.user.is_staff
        ) and post.topic.board.preferences.require_approval

    def post(self, request, *args, **kwargs):
        post = Post.objects.get(pk=self.kwargs["pk"])
        post.approved = not post.approved
        post.save()

        channel_group_send(
            f"board_{post.topic.board.slug}",
            {
                "type": "post_updated",
                "post_pk": post.pk,
            },
        )

        return HttpResponse("")


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
        board = Board.objects.get(slug=self.kwargs["slug"])
        return (
            self.request.user == board.owner
            or self.request.user in board.preferences.moderators.all()
            or self.request.user.is_staff
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["url"] = self.request.build_absolute_uri(
            reverse_lazy("boards:board", kwargs={"slug": self.kwargs["slug"]})
        )
        return context
