import json

from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse
from django.views import generic
from django_htmx.http import trigger_client_event

from boards.models import Post, Reaction
from boards.utils import get_is_moderator, post_reaction_send_update_message


class ReactionsDeleteView(UserPassesTestMixin, generic.TemplateView):
    template_name = "boards/post_reactions_confirm_delete.html"
    board_post = None

    def test_func(self):
        post = self.get_object()
        return (
            get_is_moderator(self.request.user, post.topic.board)
            and post.topic.board.preferences.reaction_type != "n"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        post = self.get_object()
        context["post"] = post
        return context

    def get_object(self):
        if not self.board_post:
            self.board_post = (
                Post.objects.prefetch_related("topic__board__owner")
                .prefetch_related("topic__board__preferences")
                .prefetch_related("topic__board__preferences__moderators")
                .get(pk=self.kwargs["pk"])
            )
        return self.board_post

    def post(self, request, *args, **kwargs):
        post = self.get_object()
        post.reactions.filter(type=post.topic.board.preferences.reaction_type).delete()
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


class PostReactionView(generic.View):
    def post(self, request, *args, **kwargs):
        post = Post.objects.get(pk=self.kwargs["pk"])
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

            has_reacted, reaction_id, reacted_score = post.get_has_reacted(request, post.reactions.all())

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

        return HttpResponse(
            status=204,
            headers={"HX-Trigger": json.dumps(to_json)},
        )
