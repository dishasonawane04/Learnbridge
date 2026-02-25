import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from ai_engine.retriever import retrieve_diverse_context
from ai_engine.llm import ask_llm
import json

def debug_gen(course_id):
    print(f"--- DEBUG GEN FOR COURSE {course_id} ---")
    context = retrieve_diverse_context(course_id, k=8)
    print(f"Retrieved context length: {len(context) if context else 0}")
    if not context:
        print("ERROR: Context is empty!")
        return

    prompt = f"""Create 3 flashcards from this:\n{context}\nOutput JSON: [{{'front': '...', 'back': '...'}}]"""
    print("Calling LLM...")
    raw = ask_llm(prompt)
    print(f"Raw LLM Response: {raw[:200]}...")
    
    try:
        data = json.loads(raw)
        print(f"Parsed cards: {len(data)}")
    except Exception as e:
        print(f"Parse error: {e}")

if __name__ == "__main__":
    debug_gen(5)
