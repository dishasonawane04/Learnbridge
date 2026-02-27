from ai_engine.vector_store import load_vector_db
from django.conf import settings
import logging
logger = logging.getLogger(__name__)

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
def retrieve_diverse_context(course_id, query=None, k=8, fetch_k=20):
    """
    Retrieve diverse context from across the entire document using MMR and randomized sampling.
    If query is provided, it prioritizes content relevant to the query while maintaining diversity.
    If vector retrieval fails or is empty, falls back to raw extracted text.
    """
    import random
    db = load_vector_db(course_id)
    raw_context = ""
    
    if db:
        logger.info(f"RAG: Retrieving {k} chunks for Course {course_id}...")
        try:
            # If no query provided, use enhanced hints for better syllabus coverage
            if not query:
                hints = ["core concepts", "definitions", "summary", "introduction", "conclusions", "details", "examples", "formulas"]
                search_query = random.choice(hints)
            else:
                search_query = query
            
            docs = db.max_marginal_relevance_search(
                search_query,
                k=k,
                fetch_k=fetch_k,
                lambda_mult=0.5
            )
            raw_context = "\n\n".join([f"[Context {i+1}]: {d.page_content}" for i, d in enumerate(docs)])
            logger.info(f"RAG: Success! Retrieved {len(docs)} chunks.")
        except Exception as e:
            logger.error(f"RAG: MMR Search failed, trying distributed fallback: {e}")
            raw_context = retrieve_distributed_context(course_id, k=k)
    
    # 2. Robust Fallback: If still no context, use full extracted text
    if not raw_context.strip():
        logger.info(f"RAG: No chunks found for Course {course_id}. Falling back to full extracted text...")
        try:
            from course.models import Course
            course = Course.objects.filter(id=course_id).first()
            if course and course.extracted_text:
                full_text = course.extracted_text.strip()
                # Use first 5,000 characters as fallback context
                raw_context = full_text[:5000]
                logger.info(f"RAG: Fallback Success! Using {len(raw_context)} chars of extracted text.")
            else:
                logger.warning(f"RAG: No extracted text found for Course {course_id}.")
        except Exception as e:
            logger.error(f"RAG: Fallback failed: {e}")

    return raw_context
