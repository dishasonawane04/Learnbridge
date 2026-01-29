from django.shortcuts import redirect
from django.contrib import messages

def teacher_required(view_func):
    """
    Decorator to restrict access to views for Teachers only.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        try:
            if request.user.userprofile.role == 'Teacher':
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Access restricted to Teachers only.")
                return redirect('dashboard')
        except:
             messages.error(request, "User profile error.")
             return redirect('dashboard')
             
    return _wrapped_view
