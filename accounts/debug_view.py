from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import UserProfile

@login_required
def debug_role(request):
    """
    A temporary view to display user role and profile information for debugging.
    """
    user = request.user
    
    # Check User attributes
    lines = [
        f"<h1>Debug Role for User: {user.username}</h1>",
        f"<p>Is Authenticated: {user.is_authenticated}</p>",
        f"<p>Is Staff: {user.is_staff}</p>",
        f"<p>Is Superuser: {user.is_superuser}</p>",
        "<hr>",
        "<h3>Profiles found:</h3>"
    ]
    
    # Check related profiles
    profiles = []
    
    # 1. Accounts UserProfile
    if hasattr(user, 'account_profile'):
        ap = user.account_profile
        profiles.append(f"<b>Account Profile (accounts app):</b> Role='{ap.role}', ID={ap.id}")
    else:
        profiles.append("<b>Account Profile:</b> NOT FOUND")
        
    # 2. Core Profile (if it exists)
    if hasattr(user, 'core_profile'):
         cp = user.core_profile
         profiles.append(f"<b>Core Profile:</b> Role='{getattr(cp, 'role', 'N/A')}', ID={cp.id}")
    else:
         profiles.append("<b>Core Profile:</b> NOT FOUND")
         
    # 3. Check for any other OneToOneField to User
    from django.apps import apps
    for model in apps.get_models():
        for field in model._meta.fields:
            if field.one_to_one and field.remote_field.model.__name__ == 'User':
                try:
                    related_obj = getattr(user, field.related_query_name() or model.__name__.lower())
                    profiles.append(f"<b>Found related model '{model.__name__}':</b> {related_obj}")
                except:
                    pass

    lines.extend([f"<ul>{''.join([f'<li>{p}</li>' for p in profiles])}</ul>"])
    
    lines.extend([
        "<hr>",
        "<p><a href='/lor/'>Try accessing LOR now</a></p>",
        "<p><a href='/'>Back to Home</a></p>"
    ])
    
    return HttpResponse("\n".join(lines))
