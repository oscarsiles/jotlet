from cacheops import cached_as
from django import template

from boards.models import Reaction

register = template.Library()


@register.simple_tag
def get_has_reacted(post, request, type):
    post_reactions = Reaction.objects.filter(post=post, type=type)
    has_reacted = False

    if request.user.is_authenticated:
        has_reacted = post_reactions.filter(user=request.user).nocache().exists()
    if request.session.session_key:
        has_reacted = post_reactions.filter(session_key=request.session.session_key).nocache().exists()

    return has_reacted
