from django.shortcuts import redirect
from django.contrib import messages

def faculty_required(view_func):
    """
    Decorator to restrict access to views for Faculty only.
    """
    def _wrapped_view(request, *args, **kwargs):
        import datetime, os
        from django.conf import settings
        
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        # Robust check for logging
        role = ''
        profile_source = 'None'
        if hasattr(request.user, 'account_profile'):
            role = getattr(request.user.account_profile, 'role', '')
            profile_source = 'account_profile'
        elif hasattr(request.user, 'core_profile'):
            role = getattr(request.user.core_profile, 'role', '')
            profile_source = 'core_profile'
            
        log_entry = f"{datetime.datetime.now()} | User: {request.user.username} | Role: '{role}' | Source: {profile_source} | Admin: {request.user.is_staff} | URL: {request.path}\n"
        try:
            with open(r'd:\DISHA\learnbridge\debug_rejections.log', 'a') as f:
                f.write(log_entry)
        except:
            pass
        print(f"DEBUG DECORATOR: {log_entry.strip()}")

        # Bypassing for sakshi and disha specifically to debug
        if request.user.username in ['sakshi', 'disha']:
            print(f"DEBUG DECORATOR: Explicitly allowing {request.user.username}")
            return view_func(request, *args, **kwargs)

        if role and role.strip().lower() in ['faculty', 'teacher']:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Access restricted to Faculty only.")
            return redirect('analytics:student_dashboard')
             
    return _wrapped_view

# Alias for backward compatibility
teacher_required = faculty_required
