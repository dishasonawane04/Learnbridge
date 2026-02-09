from django.shortcuts import redirect
from django.contrib import messages

def faculty_required(view_func):
    """
    Decorator to restrict access to views for Faculty only.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        try:
            if request.user.account_profile.role.lower() == 'faculty':
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Access restricted to Faculty only.")
                return redirect('analytics:student_dashboard')
        except Exception:
             messages.error(request, "User profile error.")
             return redirect('home')
             
    return _wrapped_view

# Alias for backward compatibility
teacher_required = faculty_required
