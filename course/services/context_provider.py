from course.models import Course
import logging

logger = logging.getLogger(__name__)

def get_course_context(user, course_id=None):
    """
    Retrieves the extracted text context for a course.
    """
    from core.ai.services import CourseContextEngine
    
    if not course_id and user and user.is_authenticated:
        # Fallback to latest course uploaded by user if no ID
        course = Course.objects.filter(user=user).order_by('-created_at').first()
        if course:
            course_id = course.id
    
    if course_id:
        return CourseContextEngine.get_course_context(course_id)
    
    return "No course material uploaded. Please upload notes first."
