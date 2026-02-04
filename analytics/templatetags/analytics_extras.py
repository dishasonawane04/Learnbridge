from django import template

register = template.Library()

@register.filter
def create_readable(value):
    """
    Converts 'question_asked' to 'Question Asked'
    """
    if not value:
        return ""
    return str(value).replace('_', ' ').title()
