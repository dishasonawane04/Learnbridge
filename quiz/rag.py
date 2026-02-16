import numpy as np
from ai_core.models import KnowledgeStore
from ai_core.embeddings import get_embedding

def retrieve_context(question, course_id, top_k=4):
    """
    RAG utility to fetch relevant chunks for a specific question.
    """
    try:
        query_vector = get_embedding(question)
        if not query_vector:
            return ""

        # Fetch all knowledge for this course
        # Note: In a production app, we'd use a vector DB filter.
        # Here we perform simple cosine similarity in-memory using ORM.
        knowledge_items = KnowledgeStore.objects.filter(course_id=course_id)
        
        scored_chunks = []
        for item in knowledge_items:
            sim = cosine_similarity(query_vector, item.embedding)
            scored_chunks.append((sim, item.content))
        
        # Sort by similarity descending
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        # Combine top K
        top_chunks = [c[1] for c in scored_chunks[:top_k]]
        return "\n\n".join(top_chunks)
        
    except Exception as e:
        print(f"RAG Retrieval Error: {e}")
        return ""

def cosine_similarity(v1, v2):
    """Simple cosine similarity."""
    a = np.array(v1)
    b = np.array(v2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
