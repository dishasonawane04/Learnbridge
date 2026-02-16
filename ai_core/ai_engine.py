from .retriever import search_course_material

def get_hybrid_response_context(question, course_id):
    """
    Decides between course context or general fallback.
    Returns: (context_text, system_prompt, is_course_aware)
    """
    if not course_id:
        return "", get_general_prompt(), False

    relevant_chunks = search_course_material(question, course_id)
    
    if relevant_chunks:
        context_text = "\n".join(relevant_chunks)
        prompt = get_course_aware_prompt()
        return context_text, prompt, True
    else:
        return "", get_general_prompt(), False

def get_course_aware_prompt():
    return (
        "You are an academic AI tutor. Answer ONLY using the provided course material. "
        "Do not invent information. Mention: 'Based on your uploaded notes'. "
        "If the answer is not present, say you could not find it in the notes."
    )

def get_general_prompt():
    return (
        "You are a helpful academic assistant. Provide a clear conceptual explanation "
        "suitable for university students. Mention: 'This is general explanation beyond the course material'."
    )
