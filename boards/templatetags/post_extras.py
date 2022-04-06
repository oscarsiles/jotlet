from django import template

from boards.utils import get_has_reacted as get_has_reacted_util

register = template.Library()


@register.simple_tag
def get_has_reacted(post, request, type):
    has_reacted, reaction_id = get_has_reacted_util(post, request, type)
    return has_reacted
