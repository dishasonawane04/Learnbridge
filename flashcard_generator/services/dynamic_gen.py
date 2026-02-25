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

def generate_flashcards_dynamic(user, course_id, count=12):
    """
    Dynamic flashcard generation with RAG, Repetition Avoidance, and Caching.
    """
    cache_key = f"flashcards_session_{user.id}_{course_id}"
    cached_cards = cache.get(cache_key)
    
    if cached_cards:
        logger.info(f"Returning cached flashcards for User {user.id}, Course {course_id}")
        return cached_cards

    # 1. Retrieve Diverse Context (RAG with Fallback)
    # Reducing k to 5 to avoid overwhelming the 1B model context window
    context = retrieve_diverse_context(course_id, k=5)
    
    # 2. Check if we have enough content to actually generate cards
    from course.models import Course
    course = Course.objects.filter(id=course_id).first()
    
    total_text_len = len(course.extracted_text or "") if course else 0
    num_materials = course.course_materials.count() if course else 0
    
    
    logger.info(f"Gen: Course {course_id} | Materials: {num_materials} | Text Length: {total_text_len} | Context Chunks: {len(context) if context else 0}")

    if not context or len(context.strip()) < 300:
        if num_materials == 0:
            print("Gen: No materials found.")
            return [{"error": "Please upload course materials to generate flashcards."}]
        elif total_text_len < 300:
            print(f"Gen: Material too short ({total_text_len} chars).")
            return [{"error": "The uploaded material is too short to generate meaningful flashcards."}]
        else:
            # This shouldn't happen with our fallback, but just in case
            print("Gen: Still not enough context after fallback.")
            return [{"error": "AI could not find enough context in the documents. Try adding more detailed material."}]

    # 3. Prepare Prompt
    # 1B models perform MUCH better with a simplified prompt and a one-shot example.
    prompt = f"""
    You are an academic tutor. Create educational flashcards based ONLY on the provided context.
    
    Context:
    {context}

    Task: Generate 10-12 distinct flashcards in a JSON array.
    
    Example Output:
    [
      {{"front": "What is the capital of France?", "back": "Paris is the capital city."}}
    ]

    CRITICAL: Output ONLY a raw JSON array. No conversational text.
    """

    # 4. Call LLM (Ollama)
    raw_response = ask_llm(prompt)
    
    # 5. Robust Parsing
    generated_cards = clean_json_response(raw_response)
    
    if not generated_cards:
        logger.error(f"Gen: LLM returned empty or invalid response for Course {course_id}.")
        logger.error(f"Raw response (first 200 chars): {str(raw_response)[:200]}")
        return [{"error": "AI could not generate valid flashcards from this material. Please try adding more detail or simplify the text."}]

    # 6. Repetition Avoidance (Discard seen cards)
    final_cards = []
    new_history_entries = []
    
    history_hashes = set(StudentFlashcardHistory.objects.filter(
        student=user, course_id=course_id
    ).values_list('card_hash', flat=True))

    logger.info(f"Gen: Received {len(generated_cards)} cards from AI. History: {len(history_hashes)}")

    for card in generated_cards:
        if not isinstance(card, dict) or 'front' not in card or 'back' not in card:
            continue
            
        c_hash = get_card_hash(card['front'])
        if c_hash in history_hashes:
            logger.info(f"Skipping repeated card: {card['front'][:30]}...")
            continue
            
        final_cards.append(card)
        new_history_entries.append(StudentFlashcardHistory(
            student=user, course_id=course_id, card_hash=c_hash
        ))

    # Handle the case where ALL cards were duplicates
    if not final_cards and generated_cards:
        logger.warning("Gen: All generated cards were duplicates.")
        return [{"error": "You've reviewed all generated flashcards for this material. Try adding new material to get fresh concepts!"}]

    # Bulk create history entries
    if new_history_entries:
        StudentFlashcardHistory.objects.bulk_create(new_history_entries, ignore_conflicts=True)

    # 6. Session Cache (10 minutes)
    if final_cards:
        cache.set(cache_key, final_cards, 600)

    return final_cards
