import json
import uuid
import hashlib
from django.conf import settings
from langchain_community.chat_models import ChatOllama
from ai_engine.retriever import retrieve_distributed_context
from quiz.models import StudentQuestionHistory

def generate_quiz(course_id, user=None, num_questions=5):
    """
    Generates a unique quiz using Distributed RAG and repetition prevention.
    """
    # 1. Retrieve Distributed Context (Full Syllabus Coverage)
    context = retrieve_distributed_context(course_id, k=4)
    
    if not context:
        return []

    import time
    seed = uuid.uuid4().hex[:8]
    
    from langchain_core.messages import SystemMessage, HumanMessage
    
    # 2. Setup LLM
    llm = ChatOllama(
        model=settings.OLLAMA_MODEL_TEXT, 
        temperature=0.9, # Maximize variety and novelty
        base_url=settings.OLLAMA_BASE_URL,
        format="json"
    )
    
    system_instruction = """You are a specialized Educational MCQ Generator. 
    Your task is to create high-quality, diverse multiple choice questions based on provided text.
    STRICT REQUIREMENTS:
    1. Output ONLY a JSON object.
    2. 'question' MUST be a complete interrogative sentence (min 10 words). DO NOT skip the question.
    3. 'options' MUST be a list of EXACTLY 4 distinct, plausible choices.
    4. 'correct_answer' MUST be one of the strings in the 'options' list.
    5. Avoid repeating the same basic definitions; focus on application and deep concepts."""

    user_prompt = f"""Generate {num_questions} NEW and UNIQUE MCQs from this text.
    Instruction Seed: {seed}

    TEXT:
    {context}

    JSON FORMAT:
    {{
      "questions": [
        {{
          "question": "What specifically happens when...?",
          "options": ["...", "...", "...", "..."],
          "correct_answer": "...",
          "explanation": "...",
          "difficulty": "Medium"
        }}
      ]
    }}"""

    try:
        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=user_prompt)
        ]
        response = llm.invoke(messages)
        content = response.content
        
        # Robust Parsing
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            import re
            cleaned = re.sub(r'```json\s*', '', content)
            cleaned = re.sub(r'```\s*', '', cleaned)
            data = json.loads(cleaned)

        questions = data.get("questions", [])
        
        formatted_questions = []
        for q in questions:
            q_text = q.get("question", "").strip()
            opts = q.get("options", [])
            
            # VALIDATION: Discard incomplete or broken questions
            if not q_text or len(q_text) < 15: continue 
            if len(opts) < 4: continue
            
            # Hashing for repetition prevention
            q_hash = hashlib.sha256(q_text.lower().encode()).hexdigest()
            
            # Check history if user is provided
            if user and StudentQuestionHistory.objects.filter(user=user, course_id=course_id, question_hash=q_hash).exists():
                continue

            correct = q.get("correct_answer") or q.get("answer")
            
            try:
                correct_index = opts.index(correct)
            except (ValueError, TypeError):
                correct_index = 0
            
            formatted_questions.append({
                "id": str(uuid.uuid4()),
                "question": q_text,
                "options": opts[:4], # Ensure exactly 4
                "correct_answer": correct,
                "correct_index": correct_index, 
                "explanation": q.get("explanation", "Based on course material analysis."),
                "difficulty": q.get("difficulty", "Medium"),
                "hash": q_hash
            })
            
        return formatted_questions

    except Exception as e:
        print(f"Quiz Generation Error: {e}")
        return []
