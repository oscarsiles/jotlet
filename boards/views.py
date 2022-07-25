import json
from urllib.parse import urlparse

from crispy_forms.helper import FormHelper
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import resolve, reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.cache import cache_control
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh, trigger_client_event

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
    except Exception:
        raise Exception(f"Could not send message: reaction_updated for reaction-{post.pk}")


class IndexView(generic.FormView):
    model = Board
    template_name = "boards/index.html"
    form_class = SearchBoardsForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()
        return context

    def form_valid(self, form):
        return HttpResponseRedirect(reverse("boards:board", kwargs={"slug": form.cleaned_data["board_slug"]}))


class IndexAllBoardsView(LoginRequiredMixin, UserPassesTestMixin, generic.TemplateView):
    model = Board
    template_name = "boards/index.html"
    permission_required = "boards.can_view_all_boards"

    def test_func(self):
        return self.request.user.has_perm(self.permission_required) or self.request.user.is_staff

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


class CreateTopicView(LoginRequiredMixin, UserPassesTestMixin, generic.CreateView):
    model = Topic
    fields = ["subject"]
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
    fields = ["subject"]
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
        response = HttpResponse(status=204)

        return trigger_client_event(
            trigger_client_event(
                response,
                "showMessage",
                {
                    "message": "Topic Posts Deleted",
                    "color": "danger",
                },
            ),
            "topicUpdated",
            None,
        )


def get_post_form(form):
    form.helper = FormHelper()
    form.helper.form_show_labels = False
    return form


class CreatePostView(UserPassesTestMixin, generic.CreateView):
    model = Post
    fields = ["content"]
    template_name = "boards/post_form.html"
    is_reply = False
    reply_to = None

    def test_func(self):
        is_allowed = True
        if "post_pk" in self.kwargs:
            self.is_reply = True
            # check if the user is allowed to reply to the post
            self.reply_to = get_post_with_prefetches(self.kwargs["slug"], self.kwargs["post_pk"])
            board = self.reply_to.topic.board

            is_allowed = board.preferences.type == "r" and (
                (self.reply_to.approved and board.preferences.allow_guest_replies)
                or get_is_moderator(self.request.user, board)
            )

        return is_allowed

    def get_form(self):
        return get_post_form(super().get_form())

    def form_valid(self, form):
        if self.is_reply:
            form.instance.topic_id = self.reply_to.topic_id
            form.instance.reply_to = self.reply_to
            form.instance.reply_depth = self.reply_to.reply_depth + 1
        else:
            form.instance.topic_id = self.kwargs.get("topic_pk")

        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()
        form.instance.session_key = self.request.session.session_key

        if self.request.user.is_authenticated:
            form.instance.user = self.request.user

        if form.instance.topic.board.preferences.require_post_approval:
            form.instance.approved = get_is_moderator(self.request.user, form.instance.topic.board)

        response = super().form_valid(form)
        response.status_code = 204

        return trigger_client_event(
            trigger_client_event(
                response,
                "showMessage",
                {
                    "message": "Post Created",
                },
            ),
            "postCreated",
            None,
        )


class UpdatePostView(UserPassesTestMixin, generic.UpdateView):
    model = Post
    board_post = None
    fields = ["content"]
    template_name = "boards/post_form.html"

    def test_func(self):
        post = self.get_object()
        return (
            self.request.session.session_key == post.session_key
            or self.request.user.has_perm("boards.change_post")
            or get_is_moderator(self.request.user, post.topic.board)
        )

    def get_form(self):
        return get_post_form(super().get_form())

    def get_object(self):
        if not self.board_post:
            self.board_post = Post.objects.prefetch_related("topic__board__preferences__moderators").get(
                pk=self.kwargs["pk"]
            )
        return self.board_post

    def form_valid(self, form):
        response = super().form_valid(form)
        response.status_code = 204

        return trigger_client_event(
            trigger_client_event(
                response,
                "showMessage",
                {
                    "message": "Post Updated",
                },
            ),
            "postUpdated",
            None,
        )


class DeletePostView(UserPassesTestMixin, generic.DeleteView):
    model = Post
    board_post = None
    template_name = "boards/post_confirm_delete.html"

    def test_func(self):
        if not self.request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            self.request.session.create()
        post = self.get_object()
        return (
            self.request.session.session_key == post.session_key
            or self.request.user.has_perm("boards.delete_post")
            or get_is_moderator(self.request.user, post.topic.board)
        )

    def get_object(self):
        if not self.board_post:
            self.board_post = Post.objects.prefetch_related("topic__board__preferences__moderators").get(
                pk=self.kwargs["pk"]
            )
        return self.board_post

    def form_valid(self, form):
        response = super().form_valid(form)
        response.status_code = 204

        return trigger_client_event(
            trigger_client_event(
                response,
                "showMessage",
                {
                    "message": "Post Deleted",
                    "color": "danger",
                },
            ),
            "postDeleted",
            None,
        )

    def get_success_url(self):
        return reverse_lazy("boards:board", kwargs={"slug": self.kwargs["slug"]})


class ReactionsDeleteView(UserPassesTestMixin, generic.TemplateView):
    template_name = "boards/post_reactions_confirm_delete.html"
    board_post = None

    def test_func(self):
        post = self.get_object()
        return get_is_moderator(self.request.user, post.topic.board)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        post = self.get_object()
        context["post"] = post
        return context

    def get_object(self):
        if not self.board_post:
            self.board_post = get_post_with_prefetches(self.kwargs["slug"], self.kwargs["pk"])
        return self.board_post

    def post(self, request, *args, **kwargs):
        post = self.get_object()
        post.reactions.all().delete()
        post_reaction_send_update_message(post)

        response = HttpResponse(status=204)

        return trigger_client_event(
            trigger_client_event(
                response,
                "showMessage",
                {
                    "message": "Reactions Deleted",
                    "color": "danger",
                },
            ),
            "reactionUpdated",
            None,
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
    board_post = None

    def test_func(self):
        self.board_post = post = Post.objects.prefetch_related("topic__board__preferences").get(pk=self.kwargs["pk"])
        return (
            get_is_moderator(self.request.user, post.topic.board)
        ) and post.topic.board.preferences.require_post_approval

    def post(self, request, *args, **kwargs):
        post = self.board_post
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

        if not request.session.session_key:  # if session is not set yet (i.e. anonymous user)
            request.session.create()

        # check if user is creator of post, and if so, don't allow them to react
        if type == "n":
            message_text = "Reactions disabled"
            message_color = "danger"
            is_updated = False
        elif post.user == request.user or post.session_key == request.session.session_key:
            message_text = "You cannot react to your own post"
            message_color = "danger"
            is_updated = False
        else:
            if type == "l":
                reaction_score = 1
            else:
                reaction_score = int(request.POST.get("score"))

            has_reacted, reaction_id, reacted_score = post.get_has_reacted(request)

            if has_reacted:
                reaction = Reaction.objects.get(id=reaction_id)
                if reaction_score == reacted_score:
                    reaction.delete()
                else:
                    reaction.reaction_score = reaction_score
                    reaction.save()
            else:
                reaction_user = request.user if request.user.is_authenticated else None

                Reaction.objects.create(
                    session_key=request.session.session_key,
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
        context["slug"] = self.kwargs["slug"]
        context["url"] = self.request.build_absolute_uri(
            reverse_lazy("boards:board", kwargs={"slug": self.kwargs["slug"]})
        )
        return context
