from ai_engine.vector_store import load_vector_db
from django.conf import settings

def retrieve_context(query, course_id, k=6):
    """
    Retrieve relevant context from the course vector store.
    """
    db = load_vector_db(course_id)
    if not db:
        return ""
        
    # Search
    docs = db.similarity_search(query, k=k)
    
    # helper to format docs
    return "\n\n".join([f"[Chunk {i+1}]: {d.page_content}" for i, d in enumerate(docs)])

def retrieve_distributed_context(course_id, k=4):
    """
    Retrieve chunks spread across the entire document to ensure syllabus coverage.
    """
    import random
    db = load_vector_db(course_id)
    if not db:
        return ""

    # Access the documents directly from the FAISS docstore
    # This is a bit of a hack but works with LangChain's FAISS wrapper
    all_docs = list(db.docstore._dict.values())
    
    if not all_docs:
        return ""

    # Select k chunks distributed across the document
    total_chunks = len(all_docs)
    if total_chunks <= k:
        selected_docs = all_docs
    else:
        # Get indices spread throughout the document
        indices = [int(i * total_chunks / k) for i in range(k)]
        # Add some randomness by shifting indices slightly
        indices = [(idx + random.randint(0, max(1, total_chunks // k - 1))) % total_chunks for idx in indices]
        selected_docs = [all_docs[idx] for idx in sorted(list(set(indices)))]

    return "\n\n".join([f"[Topic Section {i+1}]: {d.page_content}" for i, d in enumerate(selected_docs)])
