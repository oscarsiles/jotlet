from django import template
from django.conf import settings

register = template.Library()


@register.filter
def addstr(arg1, arg2):
    """concatenate arg1 & arg2"""
    return str(arg1) + str(arg2)


@register.simple_tag
def define(string):
    return string


@register.simple_tag
def get_split_string(string):
    part1 = string[: len(string) // 2]
    part2 = string[len(string) // 2 :]  # noqa
    return f"{part1} {part2}"


@register.simple_tag
def get_settings_value(name):
    return getattr(settings, name, "")
