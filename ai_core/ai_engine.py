from ai_engine.retriever import retrieve_context

def get_hybrid_response_context(question, course_id, mode='text'):
    """
    Decides between course context or general fallback.
    Returns: (context_text, system_prompt, is_course_aware)
    """
    if not course_id:
        return "", get_tutor_system_prompt(mode, has_context=False), False

    # Use the new central RAG retriever
    context_text = retrieve_context(question, course_id)
    
    # Generate prompt based on whether context was actually found
    system_prompt = get_tutor_system_prompt(mode, has_context=bool(context_text.strip()))
    
    return context_text, system_prompt, bool(context_text.strip())

def get_tutor_system_prompt(mode='text', has_context=False):
    prompt = (
        "You are the AI Tutor of the LearningBridge platform. "
        "Your role is to behave like a friendly, intelligent personal teacher for students. "
        "\n\nPRIMARY BEHAVIOR: "
        "- When a student asks a question related to the course material, answer using that content FIRST. "
        "- Explain concepts in a simple, beginner-friendly way using step-by-step explanations and examples. "
    )
    
    if has_context:
        prompt += (
            "\n\nOUTSIDE SYLLABUS: "
            "- If a question is NOT specifically related to the provided course material, answer it normally using your general knowledge. "
            "- But you MUST start the answer with: \"This is outside your uploaded course, but here is a general explanation.\""
        )
    else:
        prompt += (
            "\n\nGENERAL TEACHING: "
            "- No specific course material is available right now. Answer using your own knowledge to help the student learn."
        )

    prompt += (
        "\n\nTEACHING STYLE: "
        "- Friendly, encouraging, patient, and motivating. "
        "- Use simple language, break difficult concepts down, and use real-life examples. "
        "- Ask follow-up questions like 'Does this make sense?' or 'Want a practice question?' "
        "\n\nRESTRICTIONS: "
        "- Never mention LLM, AI, RAG, embeddings, or 'based on document'. "
        "- Never refuse educational questions. "
    )
    
    if mode == 'voice':
        prompt += (
            "\n\nVOICE MODE INSTRUCTIONS: "
            "- You are in a spoken conversation. Keep answers short (3-6 sentences). "
            "- Sound natural and avoid long paragraphs."
        )
    
    return prompt

def get_specialized_system_prompt(mode='summary'):
    if mode == 'summary':
        return (
            "You are a technical document summarizer. "
            "Your goal is to provide a dense, structured, and professional executive summary. "
            "\n\nRULES: "
            "- Use markdown headers and bullet points. "
            "- Focus ONLY on technical concepts, core objectives, and critical takeaways. "
            "- Be concise. Avoid greetings, conversational filler, or introductory phrases like 'Here is the summary'. "
            "- Stay strictly within the provided context."
        )
    return get_tutor_system_prompt()

