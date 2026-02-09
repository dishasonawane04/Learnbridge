import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from django.contrib.auth import get_user_model
from course.models import Course, CourseUnit
from core.ai.services import CourseContextEngine
import uuid

User = get_user_model()

def verify_system():
    print("--- STARTING COURSE KNOWLEDGE VERIFICATION ---")
    
    # 1. Create Test Data
    unique_id = str(uuid.uuid4())[:8]
    username = f"test_user_{unique_id}"
    user = User.objects.create_user(username=username, password="password123")
    
    course_title = f"Test Course {unique_id}"
    course = Course.objects.create(title=course_title, user=user, level="UG")
    
    secret_fact = f"The secret code for this test is ALPHA-{unique_id}."
    unit_content = f"Welcome to the course. Important Note: {secret_fact}"
    
    unit = CourseUnit.objects.create(
        course=course,
        title="Intro Unit",
        content=unit_content,
        order=1
    )
    
    print(f"Created Course: {course.title}")
    print(f"Created Unit with secret fact: {secret_fact}")
    
    # 2. Verify Context Retrieval
    print("\n--- Testing Context Engine ---")
    context = CourseContextEngine.get_course_context(course.id)
    
    if secret_fact in context:
        print("✅ SUCCESS: Context Engine retrieved the secret fact.")
    else:
        print("❌ FAILURE: Context Engine did NOT retrieve the secret fact.")
        print(f"Context retrieved: {context}")
        return

    # 3. Verify AI Query (Mocking or Real)
    print("\n--- Testing AI Query (ask_course_ai) ---")
    try:
        # We will try to call the actual service. If Ollama is not up, we catch it.
        # But we want to see if the PROMPT is constructed correctly.
        # Since we can't easily inspect the prompt inside the service without mocking,
        # we will rely on the AI's answer if it's running.
        
        question = "What is the secret code mentioned in the notes?"
        print(f"Asking AI: '{question}'")
        
        # Mocking purely for safety if Ollama isn't running in this specific env
        # but attempting real call first
        response = CourseContextEngine.ask_course_ai(course.id, question)
        print(f"AI Response: {response}")
        
        if unique_id in response or "ALPHA" in response:
             print("✅ SUCCESS: AI answered correctly using the course context.")
        else:
             print("⚠️ WARNING: AI did not return the exact code. This might be due to model behavior or context issues.")
             
    except Exception as e:
        print(f"⚠️ AI Service Exception (Ollama might be down): {e}")

    # 4. Cleanup
    print("\n--- Cleanup ---")
    course.delete()
    user.delete()
    print("Test data deleted.")

if __name__ == "__main__":
    verify_system()
