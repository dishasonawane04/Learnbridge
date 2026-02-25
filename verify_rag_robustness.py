import os
import django
import sys
import shutil

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from django.conf import settings
from ai_engine.vector_store import load_vector_db
from ai_engine.retriever import retrieve_diverse_context
from flashcard_generator.services.dynamic_gen import generate_flashcards_dynamic
from course.models import Course
from django.contrib.auth.models import User

def verify_rag_robustness():
    course_id = 5
    user = User.objects.first()
    if not user:
        print("No user found in DB.")
        return

    print(f"--- VERIFYING RAG ROBUSTNESS FOR COURSE {course_id} ---")
    
    # 1. Test Auto-Indexing
    folder_path = os.path.join(settings.MEDIA_ROOT, 'vectorstore', f'course_{course_id}')
    if os.path.exists(folder_path):
        print(f"Removing existing vector store at {folder_path} to test auto-indexing...")
        shutil.rmtree(folder_path)
    
    # Trigger retrieval which should trigger auto-indexing
    print("Step 1: Triggering retrieval to test auto-indexing...")
    context = retrieve_diverse_context(course_id, k=8)
    
    if os.path.exists(folder_path):
        print("Success: Vector store auto-created!")
    else:
        print("Failure: Vector store not created.")
        
    print(f"Context retrieved (first 100 chars): {context[:100]}...")
    
    # 2. Test Fallback (by forcing empty search)
    # We can simulate this by checking the logs since we added print statements
    # Or by passing a dummy course ID that has text but no materials/index
    print("\nStep 2: Testing Full-Text Fallback...")
    # Add a dummy course with only extracted text
    dummy_course, _ = Course.objects.get_or_create(
        title="RAG Fallback Test", 
        user=user,
        extracted_text="This is a fallback test content about artificial intelligence. It contains several concepts like neural networks, deep learning, and backpropagation." * 50
    )
    
    # Ensure no vector store exists for dummy
    dummy_folder = os.path.join(settings.MEDIA_ROOT, 'vectorstore', f'course_{dummy_course.id}')
    if os.path.exists(dummy_folder):
        shutil.rmtree(dummy_folder)
        
    # retrieve_diverse_context should auto-index or fallback
    print(f"Retrieving from dummy course {dummy_course.id}...")
    context_dummy = retrieve_diverse_context(dummy_course.id, k=8)
    print(f"Dummy Context (first 100 chars): {context_dummy[:100]}...")
    
    # 3. Test Flashcard Generation with Error Reporting
    print("\nStep 3: Testing Flashcard Generation with no material...")
    empty_course, _ = Course.objects.get_or_create(title="Empty Course", user=user)
    cards = generate_flashcards_dynamic(user, empty_course.id)
    print(f"Generated cards for empty course: {cards}")

if __name__ == "__main__":
    verify_rag_robustness()
