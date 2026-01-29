from ..models import Course, CourseUnit, CourseMaterial

def get_course_context(course_id=None, unit_id=None):
    """
    Returns a consolidated text blob of the course/unit content.
    Used as context for AI features (Quiz, Notes, etc.)
    """
    context = ""
    
    if unit_id:
        materials = CourseMaterial.objects.filter(unit_id=unit_id)
        unit = CourseUnit.objects.get(id=unit_id)
        context += f"UNIT: {unit.title}\n"
        for mat in materials:
            context += f"--- CONTENT FROM {mat.file.name} ---\n"
            context += mat.extracted_text + "\n"
            
    elif course_id:
        course = Course.objects.get(id=course_id)
        context += f"COURSE: {course.title}\nDESCRIPTION: {course.description}\n"
        units = course.units.all()
        for unit in units:
            context += f"\nUNIT: {unit.title}\n"
            for mat in unit.materials.all():
                context += mat.extracted_text + "\n"
                
    return context
