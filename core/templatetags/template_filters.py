from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Return dictionary[key] or a default empty dict/value.

    Place this file in `core/templatetags/` and load with `{% load template_filters %}`.
    """
    try:
        if dictionary is None:
            return {}
        if isinstance(dictionary, dict):
            return dictionary.get(key, {})
        # Allow access to objects with attribute/key access (e.g., QueryDict)
        return dictionary.get(key, {}) if hasattr(dictionary, 'get') else getattr(dictionary, key, {})
    except Exception:
        return {}
