import hashlib
import json
import random
import time
from django.conf import settings
from django.core.cache import cache
from ai_engine.retriever import retrieve_diverse_context
from ai_engine.llm import ask_llm
from flashcard_generator.models import StudentFlashcardHistory
from flashcard_generator.services.flashcard_ai import clean_json_response
import logging
logger = logging.getLogger(__name__)

def get_card_hash(front_text):
    return hashlib.sha256(front_text.strip().lower().encode()).hexdigest()

def generate_flashcards_dynamic(user, course_id, count=8):
    """
    Overhauled: Chunk-Based Flashcard Generation.
    Uses sequential chunks (2000 chars) to prevent timeouts.
    Includes 1-time automatic retry and validation.
    """
    from ai_engine.utils.optimization import AIContextOptimizer
    
    # Check cache first (for current chunk session)
    cache_key = f"flashcards_session_{user.id}_{course_id}"
    cached_cards = cache.get(cache_key)
    if cached_cards:
        return cached_cards

    # 1. Get the next available chunk
    context = AIContextOptimizer.get_next_flashcard_chunk(course_id)
    if not context:
        return [{"error": "No course material found. Please upload a document first."}]

    # 2. Generation Loop (with 1 automatic retry)
    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            # Explicit prompt for 1B models
            prompt = (
                "Create a list of 6 flashcards from the text below.\n"
                "Return ONLY a JSON object with this exact structure:\n"
                "{\n"
                "  \"flashcards\": [\n"
                "    {\"question\": \"...\", \"answer\": \"...\"},\n"
                "    {\"question\": \"...\", \"answer\": \"...\"}\n"
                "  ]\n"
                "}\n"
                "Keep questions and answers very concise."
            )
            
            user_msg = f"Context:\n{context}\n\nTask: {prompt}"
            
            raw_response = ask_llm(
                user_msg,
                format="json",
                num_predict=1000,
                timeout=90
            )
            
            # 3. Parsing
            generated_data = clean_json_response(raw_response)
            
            # 4. Success Handling & Mapping
            valid_cards = []
            
            # If AI returned a list of strings, pair them up as (Question, Answer)
            if isinstance(generated_data, list) and len(generated_data) > 0:
                if isinstance(generated_data[0], str):
                    logger.info(f"Fallback: Pairing strings for Course {course_id}")
                    for i in range(0, len(generated_data) - 1, 2):
                        valid_cards.append({
                            "front": generated_data[i],
                            "back": generated_data[i+1],
                            "type": "QA"
                        })
                else:
                    # Normal processing for list of dicts
                    for card in generated_data:
                        if not isinstance(card, dict): continue
                        q = card.get('question') or card.get('front') or card.get('term')
                        a = card.get('answer') or card.get('back') or card.get('definition')
                        if q and a:
                            valid_cards.append({"front": q, "back": a, "type": "QA"})
            
            # 5. Success Handling
            min_required = 5 if attempt == 0 else 3
            if len(valid_cards) >= min_required:
                AIContextOptimizer.increment_flashcard_index(course_id)
                cache.set(cache_key, valid_cards, 600)
                return valid_cards
                
            logger.warning(f"Validation failed ({len(valid_cards)} cards) on attempt {attempt+1}")
            
        except Exception as e:
            logger.error(f"Gen Error on attempt {attempt+1}: {e}")
            if attempt == max_attempts - 1:
                return [{"error": f"Internal generation error. Please try again soon."}]
            
    # If we fall through the loop
    return [{"error": "AI could not generate valid flashcards. Retrying might help."}]
