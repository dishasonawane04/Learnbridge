from ai_engine.retriever import retrieve_context
from ai_engine.llm import ask_llm
import json
import re

def generate_quiz(course_id):
    context = retrieve_context(
        "important concepts definitions formulas explanations",
        course_id
    )
    
    if not context:
        return []

    prompt = f"""
You are a university exam paper setter.

Using ONLY the study material below, generate 8 MCQ questions.

Rules:
* 4 options per question
* Only one correct answer
* No outside knowledge
* Cover different topics from the notes
* Do NOT repeat questions

Return STRICT JSON:

[
  {{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "correct_index": 0,
    "explanation": "Explain why correct answer is right in 3-5 lines"
  }}
]

Study Material:
{context}
"""
    response = ask_llm(prompt)
    
    # Robust JSON extraction
    try:
        # Try to find JSON array in the response
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.S)
        if json_match:
            return json.loads(json_match.group(0))
        return json.loads(response)
    except Exception as e:
        print(f"JSON Parsing Error: {e}")
        return []
