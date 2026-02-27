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
    Dynamic flashcard generation with RAG, Repetition Avoidance, and Caching.
    Optimized for SPEED (Simpler retrieval, smaller count, prediction limits).
    """
    cache_key = f"flashcards_session_{user.id}_{course_id}"
    cached_cards = cache.get(cache_key)
    
    if cached_cards:
        logger.info(f"Returning cached flashcards for User {user.id}, Course {course_id}")
        return cached_cards

    # 1. Faster Context Retrieval (Similarity instead of MMR for speed)
    from ai_engine.retriever import retrieve_context
    from course.models import Course
    course = Course.objects.filter(id=course_id).first()
    
    # Fast Path: If material is short, skip RAG and use full text directly
    if course and course.extracted_text and len(course.extracted_text) < 4000:
        logger.info(f"Gen: Fast Path triggered for Course {course_id} (short material)")
        context = course.extracted_text
    else:
        logger.info(f"Gen: Using standard similarity retrieval for speed.")
        context = retrieve_context("key concepts and definitions", course_id, k=5)
    
    # ... Validation remains mostly same ...
    total_text_len = len(course.extracted_text or "") if course else 0
    
    if not context or len(context.strip()) < 200:
        return [{"error": "AI could not find enough context. Please ensure your material contains clear academic concepts."}]

    # 3. Optimized Prompt & Model Constraints
    prompt = f"""
    Create 8 educational flashcards based ONLY on this context. 
    Format: JSON Array of {{"front": "...", "back": "..."}}.
    
    Context:
    {context[:3000]}
    """

    # 4. Call LLM with strict limits for speed
    raw_response = ask_llm(
        prompt, 
        num_predict=400,  # Prevent long-windedness
        top_k=20,         # Narrower sampling for faster decoding
        repeat_penalty=1.2
    )
    
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
