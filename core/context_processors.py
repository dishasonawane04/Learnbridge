from course.models import Course
from course.services.state import ActiveCourseManager

def course_context(request):
    """
    Globally provides active_course and all_user_courses for base.html navbar
    """
    if request.user.is_authenticated:
        # Get all courses for the dropdown
        if request.user.is_staff or request.user.is_superuser:
            all_user_courses = Course.objects.filter(is_deleted=False)
        else:
            all_user_courses = Course.objects.filter(user=request.user, is_deleted=False)
            
        # Get active course using centralized manager
        active_course = ActiveCourseManager.get_active_course(request)
                
        return {
            'all_user_courses': all_user_courses.order_by('title'),
            'active_course': active_course
        }
    return {}
