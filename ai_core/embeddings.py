import logging
from ai_engine.vector_store import get_embeddings_model

logger = logging.getLogger(__name__)

# Cache model instance
_model = None

def get_embedding(text):
    """
    Generates an embedding vector for the given text using local HuggingFace model.
    """
    global _model
    try:
        if _model is None:
            _model = get_embeddings_model()
        
        return _model.embed_query(text)
    except Exception as e:
        logger.error(f"Embedding generation error: {e}")
        return None
