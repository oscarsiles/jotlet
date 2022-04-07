from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Reaction


def channel_group_send(group_name, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name, message)


def get_has_reacted(post, request):
    post_reactions = Reaction.objects.filter(post=post, type=post.topic.board.preferences.reaction_type)
    has_reacted = False
    reaction_id = None
    reacted_score = 1  # default score

    if request.session.session_key:
        session_key_qs = post_reactions.filter(session_key=request.session.session_key).nocache()

        if session_key_qs.exists():
            has_reacted = True
            reaction = session_key_qs.first()
            reaction_id = reaction.id
            reacted_score = reaction.reaction_score
    if request.user.is_authenticated and not has_reacted:
        user_qs = post_reactions.filter(user=request.user).nocache()

        if user_qs.exists():
            has_reacted = True
            reaction = user_qs.first()
            reaction_id = reaction.id
            reacted_score = reaction.reaction_score

    return has_reacted, reaction_id, reacted_score
