from django import template

register = template.Library()


@register.simple_tag
def get_has_reacted(post, request):
    has_reacted, reaction_id, reacted_score = post.get_has_reacted(request)
    return has_reacted, reaction_id, reacted_score


@register.simple_tag
def get_is_owner(post, request):
    return post.get_is_owner(request)
