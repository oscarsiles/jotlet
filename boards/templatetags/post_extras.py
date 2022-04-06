from django import template

from boards.models import Reaction

register = template.Library()


@register.simple_tag
def get_sessionkey_reacted(post, request, type):
    return (
        Reaction.objects.filter(post=post, session_key=request.session.session_key, type=type).exists()
        or Reaction.objects.filter(post=post, user=request.user, type=type).exists()
    )
