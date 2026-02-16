import numpy as np
from .models import KnowledgeStore
from .embeddings import get_embedding

def cosine_similarity(v1, v2):
    """Calculates cosine similarity between two vectors."""
    v1 = np.array(v1)
    v2 = np.array(v2)
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0
    return dot_product / (norm_v1 * norm_v2)

def search_course_material(question, course_id, top_k=3, threshold=0.3):
    """
    Searches the KnowledgeStore for chunks relevant to the question.
    Returns a list of chunks if similarity exceeds the threshold.
    """
    query_vector = get_embedding(question)
    if not query_vector:
        return []

    # Fetch all chunks for the course
    chunks = KnowledgeStore.objects.filter(course_id=course_id)
    
    scored_chunks = []
    for chunk in chunks:
        if not chunk.embedding: continue
        similarity = cosine_similarity(query_vector, chunk.embedding)
        scored_chunks.append((similarity, chunk.content))
    
    # Sort by similarity descending
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Return chunks that meet the threshold
    results = [content for sim, content in scored_chunks if sim >= threshold]
    
    # FALLBACK: If nothing meets threshold but chunks exist, return top K most similar
    if not results and scored_chunks:
        print(f"RAG: No chunks met threshold {threshold}. Returning top 2 fallbacks.")
        results = [content for sim, content in scored_chunks[:2] if sim > 0]
        
    # Return top K results
    return results[:top_k]
