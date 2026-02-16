
import os
import django
import sys

# Redirect stdout to a file
sys.stdout = open("notes_size_debug.txt", "w", encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from course.models import Course, CourseNotes

try:
    course = Course.objects.filter(title__icontains="Neural Network").first()
    if not course:
        print("Course 'Neural Network' not found.")
    else:
        print(f"Found Course: {course.title} (ID: {course.id})")
        notes = CourseNotes.objects.filter(course=course).first()
        if notes:
            text_len = len(notes.extracted_text)
            print(f"CourseNotes extracted_text length: {text_len} characters")
            if text_len > 0:
                print("First 500 characters of notes:")
                print(notes.extracted_text[:500])
        else:
            print("No CourseNotes found for this course.")
            from course.models import CourseMaterial
            materials = course.course_materials.all()
            print(f"Number of materials: {materials.count()}")
            for mat in materials:
                print(f"- Material: {mat.file.name}, Extracted Text Length: {len(mat.extracted_text) if mat.extracted_text else 0}")
except Exception as e:
    print(f"Error: {e}")
finally:
    sys.stdout.close()
