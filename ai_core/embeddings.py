import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

OLLAMA_EMBED_URL = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
EMBED_MODEL = settings.OLLAMA_MODEL_EMBED

def get_embedding(text):
    """
    Generates an embedding vector for the given text using local Ollama.
    """
    try:
        response = requests.post(
            OLLAMA_EMBED_URL,
            json={
                "model": EMBED_MODEL,
                "prompt": text
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json().get('embedding')
    except Exception as e:
        logger.error(f"Embedding generation error: {e}")
        return None
