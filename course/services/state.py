from django.shortcuts import get_object_or_404
from ..models import Course, CourseContext

class ActiveCourseManager:
    """Centralized service to manage active course state and context pre-loading"""

    @staticmethod
    def set_active_course(request, course_id):
        """Sets the active course in the session and ensures context exists"""
        course = get_object_or_404(Course, id=course_id, user=request.user)
        request.session['active_course_id'] = course.id
        
        # Ensure CourseContext exists
        context, created = CourseContext.objects.get_or_create(course=course)

        # Track Study Session
        from ..models import StudySession
        StudySession.objects.get_or_create(
            user=request.user,
            course=course,
            activity_type='reading', # Default entry type
            date=models.utils.timezone.now().date() if hasattr(models, 'utils') else __import__('django.utils.timezone').utils.timezone.now().date()
        )
        return course

    @staticmethod
    def get_active_course(request):
        """Retrieves current active course from session"""
        course_id = request.session.get('active_course_id')
        if not course_id:
            return None
        return Course.objects.filter(id=course_id, user=request.user).first()

    @staticmethod
    def get_active_context(request):
        """Retrieves knowledge context for the active course"""
        course = ActiveCourseManager.get_active_course(request)
        if not course:
            return None
        return getattr(course, 'context', None)
