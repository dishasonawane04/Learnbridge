import os
import django
import sys

# Setup Django environment
sys.path.append('d:\\DISHA\\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from course.models import Course, CourseMaterial
from ai_engine.course_processor import process_document

def process_course_3():
    course_id = 3
    print(f"Checking materials for Course {course_id}...")
    
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        print("Course 3 not found.")
        return

    materials = CourseMaterial.objects.filter(course=course)
    print(f"Found {materials.count()} materials.")
    
    for mat in materials:
        if mat.file:
            path = mat.file.path
            print(f"Processing: {path}")
            if os.path.exists(path):
                success = process_document(path, course_id)
                print(f"Process result: {success}")
            else:
                print(f"File missing at path: {path}")

    # Also check course.uploaded_file
    if course.uploaded_file:
        path = course.uploaded_file.path
        print(f"Processing Main Course File: {path}")
        if os.path.exists(path):
            success = process_document(path, course_id)
            print(f"Process result: {success}")

if __name__ == "__main__":
    process_course_3()
