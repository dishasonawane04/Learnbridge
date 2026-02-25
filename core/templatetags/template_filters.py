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


@register.filter
def get_initials(user):
    """
    Returns the initials of a user.
    Priority: Profile full_name > User first_name + last_name > Username
    """
    if not user or not user.is_authenticated:
        return "G"
    
    name = ""
    try:
        # Try to get full name from account profile
        if hasattr(user, 'account_profile') and user.account_profile.full_name:
            name = user.account_profile.full_name
    except:
        pass
        
    if not name:
        if user.first_name and user.last_name:
            name = f"{user.first_name} {user.last_name}"
        elif user.first_name:
            name = user.first_name
        else:
            name = user.username
            
    parts = name.split()
    if len(parts) >= 2:
        # First letter of first word + first letter of last word
        return (parts[0][0] + parts[-1][0]).upper()
    elif len(parts) == 1:
        # Just the first letter if one word
        return parts[0][0].upper()
    return "?"
