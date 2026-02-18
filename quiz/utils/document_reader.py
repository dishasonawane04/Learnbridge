import os
from course.models import CourseMaterial
from course.services.document_parser import parse_document

def get_course_text(course):
    """
    Consolidates text from all materials associated with a course.
    """
    materials = CourseMaterial.objects.filter(course=course)
    full_text = ""
    
    for mat in materials:
        if not mat.file:
            continue
            
        file_path = mat.file.path
        if not os.path.exists(file_path):
            continue
            
        try:
            extracted_data = parse_document(file_path)
            # extracted_data is [{'page_number': i, 'text': '...'}, ...]
            for page in extracted_data:
                full_text += page.get_text() if hasattr(page, 'get_text') else page.get('text', '') + "\n"
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
    return full_text[:12000] # Limit to avoid context window issues
