import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from course.models import Course, CourseMaterial, CourseUnit, CourseNotes, ConceptMap
from notes.models import Note

def debug_course(course_id):
    try:
        course = Course.objects.get(id=course_id)
        print(f"Course: {course.title} (ID: {course_id})")
        print(f"Course Extracted Text Length: {len(course.extracted_text)}")
        
        materials = course.course_materials.all()
        print(f"Materials Count: {materials.count()}")
        for m in materials:
            print(f"  - Material: {m.file.name}")
            print(f"    Type: {m.file_type}")
            print(f"    Extracted Text Length: {len(m.extracted_text)}")
            if len(m.extracted_text) > 0:
                print(f"    Snippet: {m.extracted_text[:100]}...")
        
        notes = Note.objects.filter(course=course)
        print(f"Notes Count: {notes.count()}")
        for n in notes:
            print(f"  - Note: {n.topic} (ID: {n.id})")
            print(f"    Content Length: {len(n.content)}")
            
        units = course.units.all()
        print(f"Units Count: {units.count()}")
        for u in units:
            print(f"  - Unit: {u.title} (ID: {u.id})")
            print(f"    Content Length: {len(u.content)}")
            
        try:
            cnotes = CourseNotes.objects.get(course=course)
            print(f"CourseNotes Extracted Text Length: {len(cnotes.extracted_text)}")
        except CourseNotes.DoesNotExist:
            print("CourseNotes record not found!")
            
        maps = ConceptMap.objects.filter(course=course)
        print(f"ConceptMap Objects Count: {maps.count()}")
        for cmap in maps:
            print(f"  - Map ID: {cmap.id}")
            print(f"    Data Size: {len(str(cmap.data))} chars")
            if cmap.data:
                print(f"    Nodes: {len(cmap.data.get('nodes', []))}")
                print(f"    Edges: {len(cmap.data.get('edges', []))}")
            
    except Course.DoesNotExist:
        print("Course not found!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        debug_course(sys.argv[1])
    else:
        # Check most recent course
        last_course = Course.objects.order_by('-id').first()
        if last_course:
            debug_course(last_course.id)
        else:
            print("No courses found in DB.")
