import ollama
from django.conf import settings
import logging
logger = logging.getLogger(__name__)

def ask_llm(prompt, **kwargs):
    """Simple wrapper for Ollama chat with optional parameter control."""
    try:
        # Default options + overrides from kwargs
        options = {"temperature": 0.3}
        options.update(kwargs)
        
        client = ollama.Client(host=getattr(settings, 'OLLAMA_BASE_URL', 'http://127.0.0.1:11434'))
        response = client.chat(
            model=settings.OLLAMA_MODEL_TEXT,
            messages=[{"role": "user", "content": prompt}],
            options=options
        )
        return response["message"]["content"].strip()
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return "[]"
