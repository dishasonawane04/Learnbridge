import json
import uuid
import hashlib
from django.conf import settings
from langchain_community.chat_models import ChatOllama
from ai_engine.retriever import retrieve_distributed_context
from quiz.models import StudentQuestionHistory
from asgiref.sync import sync_to_async
import re

def generate_quiz(course_id, user=None, num_questions=5):
    """
    Generates a unique quiz using Optimized Context and repetition prevention.
    """
    from ai_engine.utils.optimization import AIContextOptimizer
    
    # 1. Retrieve Optimized Context
    # Limit num_questions to 10
    num_questions = min(int(num_questions or 5), 10)
    
    context = AIContextOptimizer.prepare_context(course_id)
    
    if not context:
        # Fallback to distributed if optimizer fails
        context = retrieve_distributed_context(course_id, k=4)
        if not context:
            return []

    seed = uuid.uuid4().hex[:8]
    from langchain_core.messages import SystemMessage, HumanMessage
    
    # 2. Setup LLM (Using lightweight model for speed)
    model_name = getattr(settings, 'OLLAMA_MODEL_TEXT', 'llama3.2:1b')
    llm = ChatOllama(
        model=model_name, 
        temperature=0.7,
        base_url=settings.OLLAMA_BASE_URL,
        format="json"
    )
    
    system_instruction = """You are a specialized Educational MCQ Generator. 
    Task: Create high-quality, diverse multiple choice questions.
    STRICT REQUIREMENTS:
    1. Output ONLY a valid JSON object.
    2. Max 10 questions.
    3. Each question: EXACTLY 4 options.
    4. Explanations: STRICTLY 1 line only.
    5. Avoid long essays or complex formatting."""

    user_prompt = f"""Generate {num_questions} NEW and UNIQUE MCQs from the provided text.
    Seed: {seed}

    TEXT:
    {context}

    JSON FORMAT:
    {{
      "questions": [
        {{
          "question": "Interrogative sentence?",
          "options": ["A", "B", "C", "D"],
          "correct_answer": "D",
          "explanation": "Short 1-2 line explanation.",
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
        return _process_quiz_response(response.content, course_id, user)

    except Exception as e:
        print(f"Quiz Generation Error: {e}")
        return []

def generate_quiz_stream(course_id, user=None, num_questions=5):
    """
    Streaming version of quiz generation.
    Yields questions one by one as they are parsed from the stream.
    """
    from ai_engine.utils.optimization import AIContextOptimizer
    from langchain_community.chat_models import ChatOllama
    from langchain_core.messages import SystemMessage, HumanMessage
    
    num_questions = min(int(num_questions or 5), 10)
    context = AIContextOptimizer.prepare_context(course_id)
    
    model_name = getattr(settings, 'OLLAMA_MODEL_TEXT', 'llama3.2:1b')
    llm = ChatOllama(
        model=model_name,
        temperature=0.7,
        base_url=settings.OLLAMA_BASE_URL,
        format="json",
        timeout=300
    )

    system_instruction = """You are a specialized Educational MCQ Generator. 
    1. Output ONLY a valid JSON object.
    2. Max 10 questions.
    3. Each question: EXACTLY 4 options.
    4. Explanations: STRICTLY 1 line only.
    5. Avoid long essays or complex formatting.
    6. JSON must have a 'questions' list."""
    
    user_prompt = f"""Generate {num_questions} NEW and UNIQUE MCQs from the provided text.
    TEXT: {context[:4000]}
    Format: JSON"""

    messages = [SystemMessage(content=system_instruction), HumanMessage(content=user_prompt)]
    
    full_content = ""
    found_questions = []

    for chunk in llm.stream(messages):
        full_content += chunk.content
        
        # Simple extraction strategy for streaming:
        # Check if we have a complete question object within the 'questions' array
        try:
            # Clean up potential markdown blocks
            clean_json = full_content.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            
            # Robust parsing for partial questions
            # We look for the pattern of a finished object in the list
            # ijson is good for this, but let's try a simpler approach if we can find a closed object
            
            # Extract questions list content
            start_idx = clean_json.find('"questions": [')
            if start_idx == -1: continue
            
            questions_part = clean_json[start_idx + 14:]
            
            # Find complete { ... } blocks
            matches = re.findall(r'\{[^{}]*\}', questions_part)
            
            for match in matches:
                try:
                    q_data = json.loads(match)
                    q_text = q_data.get("question")
                    if q_text and q_text not in [q['question'] for q in found_questions]:
                        processed = _process_quiz_response(json.dumps({"questions": [q_data]}), course_id, user)
                        if processed:
                            found_questions.append(processed[0])
                            yield processed[0]
                except:
                    continue
        except:
            continue

def _process_quiz_response(content, course_id, user):
    """Helper to parse and validate quiz JSON"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        cleaned = re.sub(r'```json\s*', '', content)
        cleaned = re.sub(r'```\s*', '', cleaned)
        data = json.loads(cleaned)

    questions = data.get("questions", [])
    formatted_questions = []
    
    for q in questions:
        q_text = q.get("question", "").strip()
        opts = q.get("options", [])
        if not q_text or len(opts) < 4: continue
        
        q_hash = hashlib.sha256(q_text.lower().encode()).hexdigest()
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
            "options": opts[:4],
            "correct_answer": correct,
            "correct_index": correct_index, 
            "explanation": q.get("explanation", "Short explanation based on material."),
            "difficulty": q.get("difficulty", "Medium"),
            "hash": q_hash
        })
    return formatted_questions
