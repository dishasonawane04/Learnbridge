
import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from course.models import Course, CourseMaterial
from django.conf import settings
from ai_engine.vector_store import load_vector_db

def verify_architecture():
    print("=== Course-Centric Architecture Verification ===")
    
    # 1. Check Course
    course = Course.objects.first()
    if not course:
        print("FAIL: No courses found in DB.")
        return
    
    print(f"Testing with Course: {course.title} (ID: {course.id})")
    
    # 2. Upload Simulation
    print("\n[1/3] Path & Auto-Processing Verification...")
    # Creating a dummy text file
    dummy_path = os.path.join(settings.MEDIA_ROOT, 'test_material.txt')
    with open(dummy_path, 'w') as f:
        f.write("This is a test of the course-centric AI. LearningBridge is an educational platform.")
    
    from django.core.files import File
    with open(dummy_path, 'rb') as f:
        material = CourseMaterial.objects.create(
            course=course,
            file=File(f, name='test_material.txt'),
            file_type='text'
        )
    
    # Expected path: courses/{id}/materials/test_material.txt
    expected_rel_path = f"courses/{course.id}/materials/test_material.txt"
    if material.file.name.endswith('test_material.txt') and f'courses/{course.id}/materials/' in material.file.name:
        print(f"SUCCESS: Material uploaded to dynamic path: {material.file.name}")
    else:
        print(f"FAIL: Unexpected material path: {material.file.name}")
        print(f"Expected fragment: {expected_rel_path}")

    # Verify auto-extraction
    if material.extracted_text:
        print(f"SUCCESS: Auto-extraction triggered. Chars: {len(material.extracted_text)}")
    else:
        print("FAIL: extracted_text is empty.")

    # 3. Vector DB Directory
    print("\n[2/3] Vector Store Standardized Paths...")
    vector_path = os.path.join(settings.MEDIA_ROOT, 'courses', str(course.id), 'vector_db')
    if os.path.exists(vector_path):
        print(f"SUCCESS: Vector DB found in standardized directory: {vector_path}")
    else:
        print(f"FAIL: Vector DB directory not found: {vector_path}")

    # 4. Retrieval Verification
    print("\n[3/3] Central Retrieval Verification...")
    from ai_engine.retriever import retrieve_context
    context = retrieve_context("What is LearningBridge?", course.id)
    if "educational platform" in context.lower():
        print("SUCCESS: RAG retrieved content from the new course-centric structure.")
    else:
        print(f"FAIL: RAG retrieval missed the test content. Context: {context[:100]}...")

    # Cleanup
    material.delete()
    if os.path.exists(dummy_path):
        os.remove(dummy_path)
    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    verify_architecture()
