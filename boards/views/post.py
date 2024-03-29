import json

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views import generic
from django_htmx.http import trigger_client_event

from boards.forms import PostCreateForm
from boards.models import Board, Post, PostImage, Topic
from boards.utils import channel_group_send, get_is_moderator


class PostFormMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["board"] = self.board
        return context

    def get_form_kwargs(self, **kwargs):
        kwargs = super().get_form_kwargs(**kwargs)
        if self.board.is_additional_data_allowed:
            kwargs["is_additional_data_allowed"] = self.board.is_additional_data_allowed
            if self.board.preferences.enable_chemdoodle:
                kwargs["additional_data_type"] = "c"
        return kwargs


class CreatePostView(UserPassesTestMixin, PostFormMixin, generic.CreateView):
    model = Post
    form_class = PostCreateForm
    template_name = "boards/post_form.html"
    is_reply = False
    parent = None
    board = None

    def test_func(self):
        topic = (
            Topic.objects.prefetch_related("board")
            .prefetch_related("board__owner")
            .prefetch_related("board__preferences")
            .prefetch_related("board__preferences__moderators")
            .get(pk=self.kwargs["topic_pk"])
        )

        is_allowed = topic.post_create_allowed(self.request)

        if "post_pk" in self.kwargs and is_allowed:
            self.is_reply = True
            # check if the user is allowed to reply to the post
            self.parent = Post.objects.get(pk=self.kwargs["post_pk"])

            is_allowed = self.parent.reply_create_allowed(self.request)

        if is_allowed:
            self.board = topic.board

        return is_allowed

    def form_valid(self, form):
        if self.is_reply:
            form.instance.topic_id = self.parent.topic_id
            form.instance.parent = self.parent
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
                trigger_client_event(
                    response,
                    "showMessage",
                    {
                        "message": "Post Created",
                    },
                ),
                "postCreated",
                None,
            ),
            "postSuccessful",
            None,
        )


class UpdatePostView(UserPassesTestMixin, PostFormMixin, generic.UpdateView):
    model = Post
    form_class = PostCreateForm
    board_post = None
    template_name = "boards/post_form.html"
    board = None

    def test_func(self):
        post = self.get_object()

        is_allowed = post.update_allowed(self.request)

        if is_allowed:
            self.board = post.topic.board

        return is_allowed

    def get_object(self):
        if not self.board_post:
            self.board_post = (
                Post.objects.prefetch_related("additional_data")
                .prefetch_related("topic__board")
                .prefetch_related("topic__board__owner")
                .prefetch_related("topic__board__preferences")
                .prefetch_related("topic__board__preferences__moderators")
                .get(pk=self.kwargs["pk"])
            )
        return self.board_post

    def get_form_kwargs(self, **kwargs):
        kwargs = super().get_form_kwargs(**kwargs)
        if self.board.is_additional_data_allowed:
            kwargs["additional_data"] = self.get_object().additional_data
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        response.status_code = 204

        return trigger_client_event(
            trigger_client_event(
                trigger_client_event(
                    response,
                    "showMessage",
                    {
                        "message": "Post Updated",
                    },
                ),
                "postUpdated",
                None,
            ),
            "postSuccessful",
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
            self.board_post = (
                Post.objects.prefetch_related("topic__board__owner")
                .prefetch_related("topic__board__preferences")
                .prefetch_related("topic__board__preferences__moderators")
                .get(pk=self.kwargs["pk"])
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


class ApprovePostsView(LoginRequiredMixin, UserPassesTestMixin, generic.TemplateView):
    template_name = "boards/posts_confirm_approve.html"
    board = None

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "topic_pk" in self.kwargs:
            context["topic"] = Topic.objects.get(pk=self.kwargs["topic_pk"])
        else:
            context["board"] = Board.objects.get(slug=self.kwargs["slug"])
        return context

    def post(self, request, *args, **kwargs):
        slug = self.kwargs["slug"]
        if "topic_pk" in self.kwargs:
            Post.objects.filter(topic__pk=self.kwargs["topic_pk"]).invalidated_update(approved=True)
            message = "All posts in topic approved"
            event = "topicUpdated"
            channel_group_send(
                f"board-{slug}",
                {
                    "type": "topic_updated",
                    "topic_pk": str(self.kwargs["topic_pk"]),
                },
            )
        else:
            Post.objects.filter(topic__board__slug=slug).invalidated_update(approved=True)
            message = "All posts in board approved"
            event = "boardUpdated"
            channel_group_send(
                f"board-{slug}",
                {
                    "type": "board_updated",
                },
            )

        response = HttpResponse(status=204)

        return trigger_client_event(
            trigger_client_event(
                response,
                "showMessage",
                {
                    "message": message,
                    "color": "success",
                },
            ),
            event,
            None,
        )


class DeletePostsView(LoginRequiredMixin, UserPassesTestMixin, generic.TemplateView):
    template_name = "boards/posts_confirm_delete.html"

    def test_func(self):
        board = Board.objects.get(slug=self.kwargs["slug"])
        return self.request.user == board.owner or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "topic_pk" in self.kwargs:
            context["topic"] = Topic.objects.get(pk=self.kwargs["topic_pk"])
        else:
            context["board"] = Board.objects.get(slug=self.kwargs["slug"])
        return context

    def post(self, request, *args, **kwargs):
        if "topic_pk" in self.kwargs:
            Post.objects.filter(topic__pk=self.kwargs["topic_pk"]).delete()
            message = "All posts in topic deleted"
            event = "topicUpdated"
        else:
            Post.objects.filter(topic__board__slug=self.kwargs["slug"]).delete()
            message = "All posts in board deleted"
            event = "boardUpdated"
        response = HttpResponse(status=204)

        return trigger_client_event(
            trigger_client_event(
                response,
                "showMessage",
                {
                    "message": message,
                    "color": "danger",
                },
            ),
            event,
            None,
        )


class PostFetchView(generic.TemplateView):
    template_name = "boards/components/post.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["board"] = board = (
            Board.objects.prefetch_related("owner")
            .prefetch_related("preferences")
            .prefetch_related("preferences__moderators")
            .prefetch_related("topics")
            .prefetch_related("topics__posts")
            .prefetch_related("topics__posts__children")
            .get(slug=self.kwargs["slug"])
        )
        context["topic"] = topic = board.topics.get(pk=self.kwargs["topic_pk"])
        context["post"] = post = topic.posts.get(pk=self.kwargs["pk"])
        if not board.preferences.require_post_approval and not post.approved:
            context["post"].approved = True
        context["is_owner"] = post.get_is_owner(self.request)
        context["is_moderator"] = get_is_moderator(self.request.user, board)
        return context


class PostFooterFetchView(generic.TemplateView):
    template_name = "boards/components/post_footer.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["board"] = board = (
            Board.objects.prefetch_related("owner")
            .prefetch_related("preferences")
            .prefetch_related("preferences__moderators")
            .get(slug=self.kwargs["slug"])
        )
        context["topic"] = topic = board.topics.get(pk=self.kwargs["topic_pk"])
        context["post"] = post = topic.posts.get(pk=self.kwargs["pk"])
        context["is_owner"] = post.get_is_owner(self.request)
        context["is_moderator"] = get_is_moderator(self.request.user, board)
        return context


class PostToggleApprovalView(LoginRequiredMixin, UserPassesTestMixin, generic.View):
    board_post = None

    def test_func(self):
        self.board_post = post = (
            Post.objects.prefetch_related("topic__board__owner")
            .prefetch_related("topic__board__preferences")
            .prefetch_related("topic__board__preferences__moderators")
            .get(pk=self.kwargs["pk"])
        )
        return (
            get_is_moderator(self.request.user, post.topic.board)
        ) and post.topic.board.preferences.require_post_approval

    def post(self, request, *args, **kwargs):
        post = self.board_post
        post.approved = not post.approved
        post.save()

        return HttpResponse(status=204)


class PostImageUploadView(UserPassesTestMixin, generic.View):
    http_method_names = ["post"]
    board = None

    def test_func(self):
        self.board = Board.objects.get(slug=self.kwargs["slug"])
        return get_is_moderator(self.request.user, self.board) and self.board.preferences.allow_image_uploads

    def post(self, request, *args, **kwargs):
        response_data = {}
        valid_image_types = ["image/png", "image/jpeg", "image/gif", "image/bmp", "image/webp"]
        image = request.FILES.get("image")

        if image.content_type not in valid_image_types:
            response_data["error"] = "Invalid image type (only PNG, JPEG, GIF, BMP, and WEBP are allowed)"
        elif image.size > settings.MAX_POST_IMAGE_FILE_SIZE:
            response_data[
                "error"
            ] = f"Image is too large (max size is {settings.MAX_POST_IMAGE_FILE_SIZE // (1024*1024)}MB)"
        elif self.board.images.count() >= settings.MAX_POST_IMAGE_COUNT:
            response_data["error"] = "Board image quota exceeded"
        else:
            im = PostImage.objects.create(image=image, board=self.board)
            file_path = {"filePath": im.image.url}
            response_data["data"] = file_path

        return HttpResponse(json.dumps(response_data), content_type="application/json")
