import ollama
from django.conf import settings
import logging
logger = logging.getLogger(__name__)

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
        logger.error(f"LLM Error: {e}")
        return "[]"
