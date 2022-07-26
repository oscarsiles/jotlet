from django import template

register = template.Library()


@register.simple_tag
def get_is_owner(post, request):
    return post.get_is_owner(request)


@register.simple_tag
def get_reactions(post, reaction_type):
    return list(post.get_reactions(reaction_type))


@register.simple_tag
def get_has_reacted(post, request, reactions):
    has_reacted, reaction_id, reacted_score = post.get_has_reacted(request, reactions)
    return has_reacted, reaction_id, reacted_score


@register.simple_tag
def get_reaction_score(post, reactions, reaction_type):
    return post.get_reaction_score(reactions, reaction_type)
