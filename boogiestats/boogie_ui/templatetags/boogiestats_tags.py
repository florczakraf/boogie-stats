from django import template

register = template.Library()


@register.filter
def attr(o, name):
    return getattr(o, name)
