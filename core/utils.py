from .models import UserActivity

def log_activity(user, app_name, topic, input_type='text', time_spent=0, quiz_score=None, outcome='completed'):
    """
    Utility to log user activity across the platform.
    """
    if not user.is_authenticated:
        return None
        
    return UserActivity.objects.create(
        user=user,
        app_name=app_name,
        topic=topic,
        input_type=input_type,
        time_spent=time_spent,
        quiz_score=quiz_score,
        outcome=outcome
    )
