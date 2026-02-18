import os
import django
import sys

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from course.models import Course, CourseMaterial
from ai_engine.course_processor import process_document

def reprocess_course(course_id):
    course = Course.objects.filter(id=course_id).first()
    if not course:
        print(f"Course {course_id} not found.")
        return

    materials = course.course_materials.all()
    print(f"Reprocessing {len(materials)} materials for Course {course.title} (ID: {course_id})")

    for material in materials:
        if material.file:
            print(f"--- Processing: {material.file.name} ---")
            success = process_document(material.file.path, course.id)
            if success:
                print(f"SUCCESS: {material.file.name}")
            else:
                print(f"FAILED: {material.file.name}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        reprocess_course(sys.argv[1])
    else:
        print("Please provide a course_id.")
