import subprocess
import json
import re

def generate_mcq(text):
    """
    Generates MCQ questions from text using local Ollama instance.
    """
    prompt = f"""
You are a university exam paper setter.

From the following syllabus content, generate 5 MCQ questions.

Rules:
- Each question must have 4 options
- Mark the correct option
- Questions must test understanding, not memorization
- Output ONLY JSON format

JSON FORMAT:
[
  {{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "answer": "B"
  }}
]

SYLLABUS:
{text}
"""

    from django.conf import settings
    model = getattr(settings, 'OLLAMA_MODEL_TEXT', 'llama3.2:1b')
    
    try:
        # Use a more direct or REST-based check if possible, but at least use the right model
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60 # Add timeout to prevent hanging
        )
        
        output = result.stdout.decode('utf-8')
        
        # Extract JSON if LLM included conversational text
        json_match = re.search(r'\[.*\]', output, re.DOTALL)
        if json_match:
            output = json_match.group(0)
            
        return json.loads(output)
    except Exception as e:
        print(f"Ollama MCQ generation error: {e}")
        return []
