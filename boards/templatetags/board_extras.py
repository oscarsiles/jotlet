from django import template

register = template.Library()


@register.simple_tag
def get_split_string(string):
    part1 = string[: len(string) // 2]
    part2 = string[len(string) // 2 :]  # noqa
    return f"{part1} {part2}"
