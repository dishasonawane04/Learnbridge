import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from course.models import Course
from course.services.concept_map import ConceptMapService
from ai_engine.concept_map_generator import generate_concept_map_data

def test_generation(course_id):
    try:
        course = Course.objects.get(id=course_id)
        print(f"Testing generation for Course: {course.title} (ID: {course_id})")
        
        # 1. Manually consolidate
        from notes.models import Note
        user = course.user
        notes_text = "\n\n".join([n.content for n in Note.objects.filter(course=course, user=user) if n.content])
        materials_text = "\n\n".join([m.extracted_text for m in course.course_materials.all() if m.extracted_text])
        units_text = "\n\n".join([u.content for u in course.units.all() if u.content])
        course_text = course.extracted_text if course.extracted_text else ""
        consolidated_text = "\n\n".join([notes_text, materials_text, units_text, course_text]).strip()
        
        print(f"Consolidated Text Length: {len(consolidated_text)}")
        if not consolidated_text:
            print("No text to process!")
            return
            
        print("Calling generate_concept_map_data...")
        # We manually call it to see prints if we add them to the generator
        map_data = generate_concept_map_data(consolidated_text)
        
        if map_data:
            print("Generation SUCCESS!")
            print(f"Nodes: {len(map_data.get('nodes', []))}")
            print(f"Edges: {len(map_data.get('edges', []))}")
            # print(json.dumps(map_data, indent=2))
        else:
            print("Generation FAILED (returned empty/None)")
            
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_generation(sys.argv[1])
    else:
        last_course = Course.objects.order_by('-id').first()
        if last_course:
            test_generation(last_course.id)
        else:
            print("No courses found.")
