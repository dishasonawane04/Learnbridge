from typing import List
from langchain_core.embeddings import Embeddings
import os
import threading

class OllamaEmbeddings(Embeddings):
    """Embeddings using Ollama's API for robustness."""
    def __init__(self, model_name=None):
        from django.conf import settings
        import ollama
        self.model = model_name or settings.OLLAMA_MODEL_TEXT
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        import ollama
        import logging
        logger = logging.getLogger(__name__)
        embeddings = []
        for text in texts:
            try:
                res = ollama.embeddings(model=self.model, prompt=text)
                embeddings.append(res['embedding'])
            except Exception as e:
                logger.error(f"Ollama Embedding Error: {e}")
                embeddings.append([0.0] * 2048) # Fallback 0-vector
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        import ollama
        import logging
        logger = logging.getLogger(__name__)
        try:
            res = ollama.embeddings(model=self.model, prompt=text)
            return res['embedding']
        except Exception as e:
            logger.error(f"Ollama Embedding Error: {e}")
            return [0.0] * 2048 # Fallback

# Cache model instance globally
_model_instance = None
_model_lock = threading.Lock()

def get_embeddings_model():
    """Centralized embeddings model initialization (Singleton Pattern)"""
    global _model_instance
    with _model_lock:
        if _model_instance is None:
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Initializing Ollama Embeddings...")
            _model_instance = OllamaEmbeddings()
    return _model_instance

def create_vector_db(chunks, course_id):
    """
    Creates and saves a FAISS vector index for a specific course.
    """
    if not chunks:
        return
        
    from langchain_community.vectorstores import FAISS
    from django.conf import settings

    embeddings = get_embeddings_model()
    db = FAISS.from_documents(chunks, embeddings)
    
    # Store in media/courses/{id}/vector_db/
    folder_path = os.path.join(settings.MEDIA_ROOT, 'courses', str(course_id), 'vector_db')
    os.makedirs(folder_path, exist_ok=True)
    
    db.save_local(folder_path)
    print(f"Vector DB saved for Course {course_id} at {folder_path}")

def load_vector_db(course_id, auto_index=True):
    """
    Loads the FAISS vector index for a course.
    Rebuilds if missing or incompatible.
    """
    from django.conf import settings
    import logging
    logger = logging.getLogger(__name__)

    embeddings = get_embeddings_model()
    folder_path = os.path.join(settings.MEDIA_ROOT, 'courses', str(course_id), 'vector_db')
    
    db = None
    if os.path.exists(folder_path):
        db = _try_load_faiss(folder_path, embeddings)

    if db is None and auto_index:
        try:
            from course.models import Course
            course = Course.objects.filter(id=course_id).first()
            if course and (course.course_materials.exists() or (course.extracted_text and len(course.extracted_text) > 100)):
                logger.info(f"Vector store missing or incompatible for Course {course_id}, triggering auto-indexing...")
                from ai_engine.course_processor import process_document
                if course.course_materials.exists():
                    for material in course.course_materials.all():
                        if material.file:
                            process_document(material.file.path, course_id)
                elif course.extracted_text:
                    from ai_engine.chunker import split_into_chunks
                    from langchain_core.documents import Document
                    chunks = split_into_chunks([Document(page_content=course.extracted_text)])
                    create_vector_db(chunks, course_id)
                
                # Try loading again after indexing
                db = _try_load_faiss(folder_path, embeddings)
        except Exception as e:
            logger.error(f"Auto-indexing failed for Course {course_id}: {e}")

    return db

def _try_load_faiss(path, embeddings):
    """Internal helper to load FAISS with error handling and dimension verification."""
    from langchain_community.vectorstores import FAISS
    import logging
    logger = logging.getLogger(__name__)
    try:
        if os.path.exists(os.path.join(path, "index.faiss")):
            db = FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
            
            # Dimension check to prevent search-time errors
            sample_text = "test query"
            model_dim = len(embeddings.embed_query(sample_text))
            index_dim = db.index.d
            
            if model_dim != index_dim:
                logger.warning(f"Dimension mismatch at {path}: Index={index_dim}, Model={model_dim}. Forcing rebuild.")
                raise ValueError("Dimension mismatch")
                
            return db
    except Exception as e:
        logger.warning(f"FAISS load failed or incompatible at {path}: {e}")
        # Try to rename incompatible index to force rebuild
        try:
            if os.path.exists(path):
                import time
                new_path = f"{path}_old_{int(time.time())}"
                os.rename(path, new_path)
                logger.info(f"Renamed incompatible index to {new_path}")
        except Exception as rename_err:
            logger.error(f"Failed to rename incompatible index: {rename_err}")
    return None
