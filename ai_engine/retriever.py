from ai_engine.vector_store import load_vector_db

def retrieve_context(query, course_id):
    db = load_vector_db(course_id)
    if not db:
        return ""
    docs = db.similarity_search(query, k=6)
    return "\n".join([d.page_content for d in docs])
