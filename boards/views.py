import json
from urllib.parse import urlparse

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import resolve, reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.cache import cache_control
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh

from .filters import BoardFilter
from .forms import BoardPreferencesForm, SearchBoardsForm
from .models import Board, BoardPreferences, Image, Post, Reaction, Topic
from .utils import channel_group_send


def get_is_moderator(user, board):
    return (
        user.has_perm("boards.can_approve_posts")
        or user in board.preferences.moderators.all()
        or user == board.owner
        or user.is_staff
    )


def get_board_with_prefetches(slug):
    board = Board.objects.select_related("preferences__background_image").get(slug=slug)
    return (
        Board.objects.select_related("owner", "preferences")
        .prefetch_related(get_topics_prefetch(board.preferences))
        .get(slug=slug)
    )


def get_topic_with_prefetches(slug, topic_pk):
    board = Board.objects.select_related("preferences").get(slug=slug)
    topic = Topic.objects.prefetch_related(
        "board__preferences",
        get_posts_prefetch(board.preferences),
    ).get(pk=topic_pk)
    return topic


def get_post_with_prefetches(slug, post_pk):
    board = Board.objects.select_related("preferences").get(slug=slug)
    post = Post.objects.prefetch_related("topic__board__preferences", get_reactions_prefetch(board.preferences)).get(
        pk=post_pk
    )
    return post


def get_topics_prefetch(preferences):
    return Prefetch(
        "topics",
        queryset=Topic.objects.prefetch_related(
            get_posts_prefetch(preferences),
        ),
    )


def get_posts_prefetch(preferences):
    qs = (
        Post.objects.prefetch_related(get_reactions_prefetch(preferences))
        if preferences.reaction_type != "n"
        else Post.objects.all()
    )
    return Prefetch("posts", queryset=qs)


def get_reactions_prefetch(preferences):
    return Prefetch(
        "reactions",
        queryset=Reaction.objects.filter(type=preferences.reaction_type).prefetch_related(
            Prefetch("user", queryset=User.objects.all())
        ),
    )


def post_reaction_send_update_message(post):
    try:
        channel_group_send(
            f"board_{post.topic.board.slug}",
            {
                "type": "reaction_updated",
                "topic_pk": post.topic.pk,
                "post_pk": post.pk,
            },
        )
    except:
        raise Exception(f"Could not send message: reaction_updated for reaction-{post.pk}")


class IndexView(generic.FormView):
    model = Board
    template_name = "boards/index.html"
    form_class = SearchBoardsForm

    def form_valid(self, form):
        self.form = form
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("boards:board", kwargs={"slug": self.form.cleaned_data["board_slug"]})


class IndexAllBoardsView(PermissionRequiredMixin, generic.TemplateView):
    model = Board
    template_name = "boards/index.html"
    permission_required = "boards.can_view_all_boards"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_all_boards"] = True
        return context


class BoardView(generic.DetailView):
    model = Board
    template_name = "boards/board_index.html"

    def get_object(self):
        return get_board_with_prefetches(self.kwargs["slug"])

    def get_template_names(self):
        template_names = super().get_template_names()
        if self.request.htmx.current_url:
            url = urlparse(self.request.htmx.current_url).path
            if url == reverse("boards:board", kwargs={"slug": self.kwargs["slug"]}):
                template_names[0] = "boards/components/board.html"

        return template_names

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()

        context["support_webp"] = self.request.META.get("HTTP_ACCEPT", "").find("image/webp") > -1
        context["is_moderator"] = get_is_moderator(self.request.user, self.object)
        return context


@method_decorator(cache_control(public=True), name="dispatch")
class BoardPreferencesView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = BoardPreferences
    template_name = "boards/components/board_preferences.html"
    form_class = BoardPreferencesForm

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def get_object(self):  # needed to prevent 'slug' FieldError
        board = Board.objects.select_related("preferences").get(slug=self.kwargs["slug"])
        if not BoardPreferences.objects.filter(board=board).exists():
            board.preferences = BoardPreferences.objects.create(board=board)
            board.preferences.save()
        return board.preferences

    def get_form_kwargs(self, **kwargs):
        kwargs = super().get_form_kwargs(**kwargs)
        kwargs["slug"] = self.kwargs["slug"]
        return kwargs

    def form_valid(self, form):
        super().form_valid(form)

        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "preferencesChanged": None,
                        "showMessage": {
                            "message": "Preferences Saved",
                            "color": "warning",
                        },
                    }
                )
            },
        )


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

        return HttpResponseClientRedirect(reverse_lazy("boards:board", kwargs={"slug": board.slug}))


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

    def form_valid(self, form):
        super().form_valid(form)

        return HttpResponseClientRefresh()


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
        super().form_valid(form)

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
        super().form_valid(form)

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
        super().form_valid(form)

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


class DeleteTopicPostsView(LoginRequiredMixin, UserPassesTestMixin, generic.TemplateView):
    template_name = "boards/topic_posts_confirm_delete.html"

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["topic"] = get_topic_with_prefetches(self.kwargs["slug"], self.kwargs["topic_pk"])
        return context

    def post(self, request, *args, **kwargs):
        topic = Topic.objects.prefetch_related("posts__reactions").get(pk=self.kwargs["topic_pk"])
        topic.posts.all().delete()

        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "topicUpdated": None,
                        "showMessage": {
                            "message": f"Topic Posts Deleted",
                            "color": "danger",
                        },
                    }
                )
            },
        )


class CreatePostView(generic.CreateView):
    model = Post
    fields = ["content"]
    template_name = "boards/post_form.html"

    def form_valid(self, form):
        form.instance.topic_id = self.kwargs.get("topic_pk")

        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()
        form.instance.session_key = self.request.session.session_key

        if self.request.user.is_authenticated:
            form.instance.user = self.request.user

        if form.instance.topic.board.preferences.require_approval:
            form.instance.approved = get_is_moderator(self.request.user, form.instance.topic.board)

        super().form_valid(form)

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
        post = Post.objects.prefetch_related("topic__board__preferences__moderators").get(pk=self.kwargs["pk"])
        return (
            self.request.session.session_key == post.session_key
            or self.request.user.has_perm("boards.change_post")
            or get_is_moderator(self.request.user, post.topic.board)
        )

    def form_valid(self, form):
        super().form_valid(form)

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
        post = Post.objects.prefetch_related("topic__board__preferences__moderators").get(pk=self.kwargs["pk"])
        return (
            self.request.session.session_key == post.session_key
            or self.request.user.has_perm("boards.delete_post")
            or get_is_moderator(self.request.user, post.topic.board)
        )

    def form_valid(self, form):
        post_pk = self.object.pk
        super().form_valid(form)

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


class ReactionsDeleteView(UserPassesTestMixin, generic.TemplateView):
    template_name = "boards/post_reactions_confirm_delete.html"

    def test_func(self):
        post = Post.objects.get(pk=self.kwargs["pk"])
        return get_is_moderator(self.request.user, post.topic.board)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        post = get_post_with_prefetches(self.kwargs["slug"], self.kwargs["pk"])
        context["post"] = post
        return context

    def post(self, request, *args, **kwargs):
        post = get_post_with_prefetches(self.kwargs["slug"], self.kwargs["pk"])
        post.reactions.all().delete()
        post_reaction_send_update_message(post)
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "reactionUpdated": None,
                        "showMessage": {
                            "message": "Reactions Deleted",
                            "color": "danger",
                        },
                    }
                )
            },
        )


# HTMX Stuff


class PaginatedFilterViews(generic.View):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET:
            querystring = self.request.GET.copy()
            if self.request.GET.get("page"):
                del querystring["page"]
            context["querystring"] = querystring.urlencode()
        return context


class BoardListView(LoginRequiredMixin, PaginatedFilterViews, generic.ListView):
    model = Board
    template_name = "boards/components/board_list.html"
    context_object_name = "boards"
    paginate_by = 5
    is_all_boards = False
    filterset = None

    def get_queryset(self):
        view = resolve(urlparse(self.request.META.get("HTTP_REFERER", "")).path).url_name
        if view == "index-all" and self.request.user.has_perm("boards.can_view_all_boards"):
            self.is_all_boards = True

        self.filterset = BoardFilter(self.request.GET, request=self.request, is_all_boards=self.is_all_boards)

        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = self.request.GET.get("page", 1)
        paginator = Paginator(self.object_list, self.paginate_by)
        page_range = paginator.get_elided_page_range(number=page, on_each_side=1, on_ends=1)

        context["filter"] = self.filterset
        context["page_range"] = page_range
        context["is_all_boards"] = self.is_all_boards
        return context


class TopicFetchView(generic.TemplateView):
    template_name = "boards/components/topic.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["topic"] = topic = get_topic_with_prefetches(self.kwargs["slug"], self.kwargs["pk"])
        context["is_moderator"] = get_is_moderator(self.request.user, topic.board)
        return context


class PostFetchView(generic.TemplateView):
    template_name = "boards/components/post.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["post"] = post = get_post_with_prefetches(self.kwargs["slug"], self.kwargs["pk"])
        context["is_owner"] = post.get_is_owner(self.request)
        context["is_moderator"] = get_is_moderator(self.request.user, post.topic.board)
        return context


class PostFooterFetchView(generic.TemplateView):
    template_name = "boards/components/post_footer.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["post"] = post = get_post_with_prefetches(self.kwargs["slug"], self.kwargs["pk"])
        context["is_owner"] = post.get_is_owner(self.request)
        context["is_moderator"] = get_is_moderator(self.request.user, post.topic.board)
        return context


class PostToggleApprovalView(LoginRequiredMixin, UserPassesTestMixin, generic.View):
    def test_func(self):
        post = Post.objects.prefetch_related("topic__board__preferences").get(pk=self.kwargs["pk"])
        return (
            get_is_moderator(self.request.user, post.topic.board)
        ) and post.topic.board.preferences.require_approval

    def post(self, request, *args, **kwargs):
        post = Post.objects.get(pk=self.kwargs["pk"])
        post.approved = not post.approved
        post.save()

        return HttpResponse(status=204)


class PostReactionView(generic.View):
    def post(self, request, *args, **kwargs):
        post = get_post_with_prefetches(self.kwargs["slug"], self.kwargs["pk"])
        type = post.topic.board.preferences.reaction_type
        message_text = "Reaction Saved"
        message_color = "success"
        is_updated = True

        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()

        # check if user is creator of post, and if so, don't allow them to react
        if post.user == self.request.user or post.session_key == self.request.session.session_key:
            message_text = "You cannot react to your own post"
            message_color = "danger"
            is_updated = False
        else:
            if type == "l":
                reaction_score = 1
            elif type == "n":
                pass
            else:
                reaction_score = int(self.request.POST.get("score", ""))

            has_reacted, reaction_id, reacted_score = post.get_has_reacted(self.request)

            if has_reacted:
                reaction = Reaction.objects.get(id=reaction_id)
                if reaction_score == reacted_score:
                    reaction.delete()
                else:
                    reaction.reaction_score = reaction_score
                    reaction.save()
            else:
                reaction_user = self.request.user if self.request.user.is_authenticated else None

                reaction = Reaction.objects.create(
                    session_key=self.request.session.session_key,
                    user=reaction_user,
                    post=post,
                    type=type,
                    reaction_score=reaction_score,
                )

        to_json = {
            "showMessage": {
                "message": message_text,
                "color": message_color,
            },
        }
        if is_updated:
            post_reaction_send_update_message(post)
            to_json["reactionUpdated"] = None

        return HttpResponse(
            status=204,
            headers={"HX-Trigger": json.dumps(to_json)},
        )


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
        context["url"] = self.request.build_absolute_uri(
            reverse_lazy("boards:board", kwargs={"slug": self.kwargs["slug"]})
        )
        return context
