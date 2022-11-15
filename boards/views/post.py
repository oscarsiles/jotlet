import json

from crispy_forms.helper import FormHelper
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views import generic
from django_htmx.http import trigger_client_event

from boards.models import Board, Post, PostImage, Topic
from boards.utils import channel_group_send, get_is_moderator


def get_post_form(form):
    form.helper = FormHelper()
    form.helper.form_show_labels = False
    return form


class CreatePostView(UserPassesTestMixin, generic.CreateView):
    model = Post
    fields = ["content"]
    template_name = "boards/post_form.html"
    is_reply = False
    parent = None

    def test_func(self):
        board = (
            Board.objects.select_related("owner")
            .select_related("preferences")
            .prefetch_related("preferences__moderators")
            .get(slug=self.kwargs["slug"])
        )
        is_allowed = board.is_posting_allowed or self.request.user == board.owner or self.request.user.is_staff
        if "post_pk" in self.kwargs and is_allowed:
            self.is_reply = True
            # check if the user is allowed to reply to the post
            self.parent = Post.objects.get(pk=self.kwargs["post_pk"])

            is_allowed = board.preferences.type == "r" and (
                (self.parent.approved and board.preferences.allow_guest_replies)
                or get_is_moderator(self.request.user, board)
            )

        return is_allowed

    def get_form(self):
        return get_post_form(super().get_form())

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
            self.board_post = (
                Post.objects.select_related("topic__board__owner")
                .select_related("topic__board__preferences")
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
            self.board_post = (
                Post.objects.select_related("topic__board__owner")
                .select_related("topic__board__preferences")
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
                    "topic_pk": self.kwargs["topic_pk"],
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
            Board.objects.select_related("owner")
            .select_related("preferences")
            .prefetch_related("preferences__moderators")
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
            Board.objects.select_related("owner")
            .select_related("preferences")
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
            Post.objects.select_related("topic__board__owner")
            .select_related("topic__board__preferences")
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
        return self.board.preferences.allow_image_uploads

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
