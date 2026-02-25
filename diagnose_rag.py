import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from course.models import Course, CourseMaterial
from ai_engine.vector_store import load_vector_db

def diagnose_course(course_id):
    try:
        course = Course.objects.get(id=course_id)
        print(f"Course: {course.id} - {course.title}")
        
        mats = course.course_materials.all()
        print(f"Materials found: {mats.count()}")
        for m in mats:
            print(f"  - Material {m.id}: {m.file.name}, Text Length: {len(m.extracted_text or '')}")
            if not m.extracted_text:
                print(f"    WARNING: No extracted text for material {m.id}")

        db = load_vector_db(course_id)
        if not db:
            print("ERROR: Vector DB could not be loaded (load_vector_db returned None)")
        else:
            # Check number of vectors
            try:
                num_vectors = db.index.ntotal
                print(f"Vector DB loaded successfully. Number of vectors: {num_vectors}")
                if num_vectors == 0:
                    print("WARNING: Vector DB exists but is EMPTY.")
            except Exception as e:
                print(f"Error checking vector count: {e}")

    except Exception as e:
        print(f"Diagnostic Error: {e}")

if __name__ == "__main__":
    diagnose_course(5)
