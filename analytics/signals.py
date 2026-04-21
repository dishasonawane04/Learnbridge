from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import ActivityLog
from django.utils import timezone

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Automatically logs a system event when a user logs in.
    """
    # Check if we already logged a login for this user today to avoid duplicates
    today = timezone.now().date()
    already_logged = ActivityLog.objects.filter(
        user=user,
        app_name='system',
        activity_type='login',
        timestamp__date=today
    ).exists()
    
    if not already_logged:
        ActivityLog.objects.create(
            user=user,
            app_name='system',
            activity_type='login',
            topic='User Session Start',
            metadata={'ip': request.META.get('REMOTE_ADDR')}
        )
