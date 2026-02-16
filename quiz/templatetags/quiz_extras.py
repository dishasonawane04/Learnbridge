from django import template
import builtins

register = template.Library()

@register.filter(name='chr')
def chr_filter(value):
    try:
        return builtins.chr(int(value))
    except (ValueError, TypeError):
        return ""
