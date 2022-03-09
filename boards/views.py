import json
from urllib.parse import urlparse

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import resolve, reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.cache import cache_control
from django.views.generic.edit import FormMixin, ProcessFormView
from django_htmx.http import HttpResponseClientRefresh

from .forms import BoardPreferencesForm, SearchBoardsForm
from .models import Board, BoardPreferences, Image, Post, Topic


def channel_group_send(group_name, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name, message)


class IndexView(FormMixin, ProcessFormView, generic.ListView):
    model = Board
    template_name = "boards/index.html"
    form_class = SearchBoardsForm
    context_object_name = "boards"
    paginate_by = 5
    object_list = ""

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop("object_list", None)
        if queryset is None and self.request.user.is_authenticated:
            self.object_list = self.model.objects.filter(owner=self.request.user).order_by("created_at")
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        self.form = form
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("boards:board", kwargs={"slug": self.form.cleaned_data["board_slug"]})


class IndexAllBoardsView(PermissionRequiredMixin, generic.ListView):
    model = Board
    template_name = "boards/index.html"
    context_object_name = "boards"
    paginate_by = 5
    permission_required = "boards.can_view_all_boards"

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop("object_list", None)
        if queryset is None:
            queryset = self.object_list = self.model.objects.all().order_by("created_at")
        context = super().get_context_data(**kwargs)
        page = self.request.GET.get("page", 1)
        paginator = Paginator(self.model.objects.all().order_by("created_at"), self.paginate_by)
        page_range = paginator.get_elided_page_range(number=page, on_each_side=1, on_ends=1)

        context["page_range"] = page_range
        context["is_all_boards"] = True
        return context


class BoardView(generic.DetailView):
    model = Board
    template_name = "boards/board_index.html"

    def get_context_data(self, **kwargs):
        context = super(BoardView, self).get_context_data(**kwargs)
        context["topics"] = Topic.objects.filter(board=self.object)

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
            board.preferences.save()
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
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "topicCreated": None,
                        "showMessage": {
                            "message": f'Topic "{self.object.subject}" created',
                        },
                    }
                )
            },
        )


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
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "topicUpdated": None,
                        "showMessage": {
                            "message": f'Topic "{self.object.subject}" updated',
                        },
                    }
                )
            },
        )


class DeleteTopicView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    model = Topic
    template_name = "boards/topic_confirm_delete.html"

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def form_valid(self, form):
        topic_pk = self.object.pk
        topic_subject = self.object.subject
        super(DeleteTopicView, self).form_valid(form)
        channel_group_send(
            f"board_{self.kwargs.get('slug')}",
            {
                "type": "topic_deleted",
                "topic_pk": topic_pk,
            },
        )
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "topicDeleted": None,
                        "showMessage": {
                            "message": f'Topic "{topic_subject}" Deleted',
                            "color": "danger",
                        },
                    }
                )
            },
        )

    def get_success_url(self):
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
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "postCreated": None,
                        "showMessage": {
                            "message": "Post Created",
                        },
                    }
                )
            },
        )


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
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "postUpdated": None,
                        "showMessage": {
                            "message": "Post Updated",
                        },
                    }
                )
            },
        )


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

    def form_valid(self, form):
        post_pk = self.object.pk
        super(DeletePostView, self).form_valid(form)
        channel_group_send(
            f"board_{self.kwargs.get('slug')}",
            {
                "type": "post_deleted",
                "post_pk": post_pk,
            },
        )
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "postDeleted": None,
                        "showMessage": {
                            "message": "Post Deleted",
                            "color": "danger",
                        },
                    }
                )
            },
        )

    def get_success_url(self):
        return reverse_lazy("boards:board", kwargs={"slug": self.kwargs["slug"]})


# HTMX Stuff


class SearchBoardView(LoginRequiredMixin, generic.ListView):
    model = Board
    template_name = "boards/components/board_list.html"
    context_object_name = "boards"
    paginate_by = 5
    is_all_boards = False

    def get_queryset(self):
        view = resolve(urlparse(self.request.META["HTTP_REFERER"]).path).url_name
        if view == "index":
            queryset = Board.objects.filter(owner=self.request.user)
        elif view == "index-all" and self.request.user.has_perm("boards.can_view_all_boards"):
            queryset = Board.objects.all()
            self.is_all_boards = True

        u = self.request.GET.get("u")
        if u:
            users = u.split(",")
            queryset = queryset.filter(owner__username__in=users)

        b = self.request.GET.get("b")
        if b:
            queryset = queryset.filter(Q(title__icontains=b) | Q(description__icontains=b))

        return queryset.order_by("created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = self.request.GET.get("page", 1)
        paginator = Paginator(self.object_list, self.paginate_by)
        page_range = paginator.get_elided_page_range(number=page, on_each_side=1, on_ends=1)

        context["page_range"] = page_range
        context["is_all_boards"] = self.is_all_boards
        return context


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

        return HttpResponse(status=204)


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
