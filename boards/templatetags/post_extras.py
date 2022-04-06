from cacheops import cached_as
from django import template

from boards.models import Reaction

register = template.Library()


@register.simple_tag
def get_has_reacted(post, request, type):
    post_reactions = Reaction.objects.filter(post=post, type=type)

    return (
        post_reactions.filter(session_key=request.session.session_key).nocache().exists()
        or post_reactions.filter(user=request.user, type=type).nocache().exists()
    )
