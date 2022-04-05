from django import template

from boards.models import Reaction

register = template.Library()


@register.simple_tag
def get_sessionkey_reacted(post, session_key, type):
    return Reaction.objects.filter(post=post, session_key=session_key, type=type).exists()
