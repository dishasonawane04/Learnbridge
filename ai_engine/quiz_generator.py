import json
import uuid
import hashlib
from django.conf import settings
from langchain_community.chat_models import ChatOllama
from ai_engine.retriever import retrieve_distributed_context
from quiz.models import StudentQuestionHistory
from asgiref.sync import sync_to_async
import re
from langchain_core.messages import SystemMessage, HumanMessage
from ai_engine.utils.optimization import AIContextOptimizer
from course.models import Course


def generate_quiz(course_id, user=None, num_questions=5):
    """
    Generates a unique quiz using Sequential Chunk Optimization.
    """
    
    # Requirement #8: Limit to 5 questions for speed
    num_questions = 5
    
    # Requirement #1 & #2: Get a random unused sequential chunk
    context = AIContextOptimizer.get_next_quiz_chunk(course_id)
    course = Course.objects.filter(id=course_id).first()
    
    is_fallback = False
    if not context:
        if course:
            context = f"Topic: {course.title} ({course.subject}). Level: {course.level}."
            is_fallback = True
        else:
            return []

    seed = uuid.uuid4().hex[:8]
    
    # Requirement #5: Retry Logic & Guarantee 5 Questions
    max_retries = 3
    final_results = []
    seen_hashes = set()
    
    for attempt_idx in range(max_retries):
        if len(final_results) >= 5: break
        
        try:
            model_name = getattr(settings, 'OLLAMA_MODEL_TEXT', 'llama3.2:1b')
            llm = ChatOllama(
                model=model_name, 
                temperature=0.8,
                base_url=settings.OLLAMA_BASE_URL,
                format="json",
                timeout=120 
            )
            
            # Requirement #7 & #2: Improved Prompt & Force Structure
            system_instruction = """Professional MCQ Generator.
            STRICT JSON OUTPUT ONLY.
            Generate 5 unique multiple-choice quiz questions from the following text. 
            Each question must include 4 options, one correct answer, and a short explanation.
            
            SCHEMA:
            {
              "questions": [
                {
                  "question": "string",
                  "options": ["string", "string", "string", "string"],
                  "correct_answer": "string",
                  "explanation": "string"
                }
              ]
            }"""

            mode_text = "from the specific course section provided" if not is_fallback else "general educational knowledge"
            user_prompt = f"""Generate 5 unique MCQs {mode_text}.
            Ensure these questions are high-quality and directly based on the context.
            SEED: {uuid.uuid4().hex[:8]}
            
            CONTEXT CHUNK:
            {context[:3000]}"""

            messages = [
                SystemMessage(content=system_instruction),
                HumanMessage(content=user_prompt)
            ]
            response = llm.invoke(messages)
            results = _process_quiz_response(response.content, course_id, user)
            
            for r in results:
                if r['hash'] not in seen_hashes:
                    seen_hashes.add(r['hash'])
                    final_results.append(r)
            
            if len(final_results) >= 5:
                return final_results[:5]
            
        except Exception as e:
            logger.error(f"Quiz Generation Attempt {attempt_idx + 1} Error: {e}")
            
    return final_results if len(final_results) > 0 else []

def generate_quiz_stream(course_id, user=None, num_questions=5):
    """
    Streaming version using random unused chunks.
    """
    # Support for internal retry
    max_retries = 2
    for attempt in range(max_retries):
        context = AIContextOptimizer.get_next_quiz_chunk(course_id)
        course = Course.objects.filter(id=course_id).first()
        
        is_fallback = False
        if not context:
            if course:
                context = f"Topic: {course.title} ({course.subject}). Level: {course.level}."
                is_fallback = True
            else:
                return
        
        model_name = getattr(settings, 'OLLAMA_MODEL_TEXT', 'llama3.2:1b')
        llm = ChatOllama(
            model=model_name,
            temperature=0.8,
            base_url=settings.OLLAMA_BASE_URL,
            format="json",
            timeout=120
        )

        system_instruction = """Professional MCQ Generator.
        STRICT JSON OUTPUT ONLY.
        Generate 5 unique multiple-choice quiz questions from the following text. 
        Each question must include 4 options, one correct answer, and a short explanation.
        
        SCHEMA:
        {
          "questions": [
            {
              "question": "string",
              "options": ["string", "string", "string", "string"],
              "correct_answer": "string",
              "explanation": "string"
            }
          ]
        }"""
        
        mode_text = "from context" if not is_fallback else "general knowledge"
        user_prompt = f"Generate 5 unique MCQs {mode_text}.\nSEED: {uuid.uuid4().hex[:8]}\nCONTEXT: {context[:3000]}\nJSON Format ONLY."
        
        system_instruction = system_instruction.replace("    ", "") # Cleanup

        messages = [SystemMessage(content=system_instruction), HumanMessage(content=user_prompt)]
        
        full_content = ""
        found_questions_count = 0
        found_hashes = set()
        brace_count = 0
        current_obj = ""
        in_questions_list = False

        try:
            for chunk in llm.stream(messages):
                token = chunk.content
                full_content += token
                
                # Check if we've entered the questions list
                if not in_questions_list and '"questions": [' in full_content:
                    in_questions_list = True
                    # Reset content to start of list content to save memory/processing
                    start_idx = full_content.find('"questions": [') + 14
                    full_content = full_content[start_idx:]
                
                if in_questions_list:
                    for char in token:
                        if char == '{':
                            brace_count += 1
                        
                        if brace_count > 0:
                            current_obj += char
                            
                        if char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                # We have a complete object
                                try:
                                    # Validate and process
                                    processed = _process_quiz_response(json.dumps({"questions": [json.loads(current_obj)]}), course_id, user)
                                    if processed:
                                        q_final = processed[0]
                                        q_hash = q_final.get('hash')
                                        if q_hash not in found_hashes:
                                            found_hashes.add(q_hash)
                                            found_questions_count += 1
                                            yield q_final
                                except:
                                    pass # Partial or malformed object
                                current_obj = ""
            
            if found_questions_count > 0:
                return # Success
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            continue

def _process_quiz_response(content, course_id, user):
    """Helper to parse and validate quiz JSON"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        cleaned = re.sub(r'```json\s*', '', content)
        cleaned = re.sub(r'```\s*', '', cleaned)
        try:
            data = json.loads(cleaned)
        except:
            return []

    questions = data.get("questions", [])
    formatted_questions = []
    
    for q in questions:
        q_text = q.get("question", "").strip()
        opts = q.get("options", [])
        correct = q.get("correct_answer") or q.get("answer")
        explanation = q.get("explanation", "").strip()
        
        # Requirement #8: Validate required fields
        if not q_text or len(opts) < 4 or not correct or not explanation:
            continue
        
        q_hash = hashlib.sha256(q_text.lower().encode()).hexdigest()
        if user and StudentQuestionHistory.objects.filter(user=user, course_id=course_id, question_hash=q_hash).exists():
            continue

        correct = q.get("correct_answer") or q.get("answer")
        correct_index = 0
        
        # Robust Index Logic
        # 1. Try exact string match
        if correct in opts:
            correct_index = opts.index(correct)
        # 2. Try Letter-based match (A, B, C, D)
        elif isinstance(correct, str) and len(correct) == 1 and correct.upper() in ['A', 'B', 'C', 'D']:
            letter_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
            correct_index = letter_map[correct.upper()]
        # 3. Try integer index
        elif isinstance(correct, int) and 0 <= correct < 4:
            correct_index = correct
        
        formatted_questions.append({
            "id": str(uuid.uuid4()),
            "question": q_text,
            "options": opts[:4],
            "correct_answer": opts[correct_index], # Store the actual text
            "correct_index": correct_index, 
            "explanation": q.get("explanation", "Based on the course material provided."),
            "difficulty": q.get("difficulty", "Medium"),
            "hash": q_hash
        })
    return formatted_questions
