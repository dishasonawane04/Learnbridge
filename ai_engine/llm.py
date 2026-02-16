import ollama
from django.conf import settings

def ask_llm(prompt):
    """Simple wrapper for Ollama chat."""
    try:
        response = ollama.chat(
            model=settings.OLLAMA_MODEL_TEXT,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3}
        )
        return response["message"]["content"].strip()
    except Exception as e:
        print(f"LLM Error: {e}")
        return "[]"
