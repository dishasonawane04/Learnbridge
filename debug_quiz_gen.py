
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from course.models import Course
from quiz.views import generate_quiz_questions
from ai_core.retriever import search_course_material

def debug_quiz():
    print("--- DEBUGGING QUIZ GENERATION ---")
    course = Course.objects.filter(title__icontains="Neural Network").first()
    if not course:
        print("Course not found.")
        return

    print(f"Testing Course: {course.title} (ID: {course.id})")
    
    # 1. Test Retrieval
    subject = "Neural Network"
    chunks = search_course_material(subject, course.id)
    print(f"\nChunks found through RAG for '{subject}': {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"Chunk {i+1} (Length {len(c)}): {c[:100]}...")

    # 2. Test Generation
    print("\nCalling generate_quiz_questions...")
    import ollama
    from django.conf import settings
    
    # Manually run the guts for debugging
    context_text = "\n".join(chunks) if chunks else ""
    context_text = context_text[:2000] # Truncate for testing
    if not context_text:
        from core.ai.services import CourseContextEngine
        context_text = CourseContextEngine.get_course_context(course.id)
        context_text = context_text[:2000] # Truncate for testing
        print(f"Fallback context found: {len(context_text)} chars")

    system_prompt = (
        "Instructions: Based on the provided study notes, create exactly 5 academic questions. "
        "Focus on the technical concepts mentioned in the text.\n"
        f"\n--- STUDY NOTES ---\n{context_text}\n---------------\n"
    )

    task_prompt = """Create 5 questions about {subject}. 
Use this format exactly:

TYPE: MCQ
Q: [Question]
A: [Choice 1]
B: [Choice 2]
C: [Choice 3]
D: [Choice 4]
ANSWER: [A, B, C, or D]

TYPE: SHORT
Q: [Question]
ANSWER: [Short text answer]

---
Begin:"""
    
    final_prompt = f"{system_prompt}\n\n{task_prompt}"
    
    print("Querying Ollama directly for debug...")
    response = ollama.chat(
        model=settings.OLLAMA_MODEL_TEXT,
        messages=[{"role": "user", "content": final_prompt}]
    )
    
    ai_text = response["message"]["content"]
    print(f"\nAI Response Content length: {len(ai_text)}")
    with open("ai_response.txt", "w", encoding="utf-8") as f:
        f.write(ai_text)
    
    from quiz.views import parse_questions
    questions = parse_questions(ai_text)
    print(f"\nQuestions generated: {len(questions)}")
    for q in questions:
        print(f"- {q.get('question')}")

if __name__ == "__main__":
    debug_quiz()
