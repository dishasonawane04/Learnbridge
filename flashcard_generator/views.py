from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from django.core.cache import cache
import json
import os
from .models import FlashcardDeck, Flashcard
from .services.flashcard_ai import generate_flashcards, explain_card_content, generate_quiz_from_cards
from analytics.models import ActivityLog
from course.models import CourseUnit, Course
from course.services.state import ActiveCourseManager
from core.ai.services import CourseContextEngine
from .services.dynamic_gen import generate_flashcards_dynamic
import logging
logger = logging.getLogger(__name__)

def flashcard_home(request):
    # Get decks ordered by creation
    decks = FlashcardDeck.objects.all().order_by('-created_at')
    
    # Calculate global stats (mock for now, or real simple counts)
    total_decks = decks.count()
    total_cards = Flashcard.objects.count()
    
    return render(request, "flashcard_generator/index.html", {
        'decks': decks,
        'total_decks': total_decks,
        'total_cards': total_cards
    })

def study_deck_view(request, deck_id):
    deck = get_object_or_404(FlashcardDeck, id=deck_id)
    return render(request, "flashcard_generator/flashcards.html", {'deck': deck})

def progress_view(request):
    """
    Displays learning statistics and progress.
    """
    decks = FlashcardDeck.objects.all()
    total_cards = Flashcard.objects.count()
    
    # Calculate box distribution (Leitner System)
    # Box 1: New/Hard, Box 5: Mastered
    box_stats = {
        'New': Flashcard.objects.filter(box=1).count(),
        'Learning': Flashcard.objects.filter(box__range=(2, 3)).count(),
        'Review': Flashcard.objects.filter(box__range=(4, 5)).count(),
        'Mastered': Flashcard.objects.filter(box__gt=5).count()
    }
    
    return render(request, "flashcard_generator/progress.html", {
        'decks': decks,
        'total_cards': total_cards,
        'box_stats': box_stats
    })

@csrf_exempt
def generate_deck_api(request):
    if request.method == "POST":
        try:
            # 1. Handle Input
            title = request.POST.get("title", "New Deck")
            difficulty = request.POST.get("difficulty", "Medium")
            text_input = request.POST.get("text_input", "")
            
            uploaded_file = request.FILES.get("file")
            file_path = None
            
            if uploaded_file:
                 fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads'))
                 filename = fs.save(uploaded_file.name, uploaded_file)
                 file_path = fs.path(filename)

            if not text_input and not file_path:
                return JsonResponse({"error": "No content provided"}, status=400)

            # 2. Call AI
            cards_data = generate_flashcards(text_input, file_path, difficulty)
            
            if not cards_data:
                 return JsonResponse({"error": "AI could not generate cards. Please try different content or add more details."}, status=500)

            # 3. Save to DB
            deck = FlashcardDeck.objects.create(title=title, difficulty=difficulty)
            
            count = 0
            for card in cards_data:
                # Validate keys
                if 'front' in card and 'back' in card:
                    Flashcard.objects.create(
                        deck=deck,
                        front=card['front'],
                        back=card['back'],
                        difficulty=card.get('difficulty', difficulty),
                        card_type=card.get('type', 'QA'),
                        exam_tip=card.get('exam_tip', "")
                    )
                    count += 1
            
            if count == 0:
                 deck.delete()
                 return JsonResponse({"error": "Parsed content but found no valid cards."}, status=500)

            # --- ANALYTICS LOGGING ---
            if request.user.is_authenticated:
                ActivityLog.objects.create(
                    user=request.user,
                    app_name='flashcard',
                    activity_type='deck_generated',
                    topic=deck.title,
                    metadata={'deck_id': str(deck.id), 'card_count': count}
                )
            # -------------------------

            return JsonResponse({"status": "success", "deck_id": deck.id, "count": count})

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=500)
            
    return JsonResponse({"error": "Invalid method"}, status=405)

def get_deck_api(request, deck_id):
    """
    Returns cards for a deck. 
    Implements Adaptive Logic: Prioritizes cards due for review.
    """
    deck = get_object_or_404(FlashcardDeck, id=deck_id)
    
    # Adaptive Strategy:
    # 1. Get cards due for review (next_review_date <= now)
    # 2. Then get new cards (box=1, review_count=0)
    # 3. Then get others
    
    now = timezone.now()
    due_cards = deck.cards.filter(next_review_date__lte=now).order_by('next_review_date')
    other_cards = deck.cards.filter(next_review_date__gt=now).order_by('next_review_date')
    
    # Combine (Due first)
    # We serialize them all, frontend can handle the focused session flow, 
    # but strictly speaking we might want to only send a batch. 
    # For this app, sending all is fine as decks aren't massive.
    
    all_cards = list(due_cards) + list(other_cards)
    
    data = [{
        "id": c.id,
        "front": c.front,
        "back": c.back,
        "difficulty": c.difficulty,
        "type": c.card_type,
        "exam_tip": c.exam_tip,
        "box": c.box,
        "is_due": c.next_review_date <= now
    } for c in all_cards]
    
    return JsonResponse({"title": deck.title, "cards": data})
    
@csrf_exempt
def update_card_progress(request, card_id):
    """
    Handles 'Easy', 'Medium', 'Hard' responsese from user.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            outcome = data.get("outcome") # 'easy', 'medium', 'hard', 'reset'
            
            card = get_object_or_404(Flashcard, id=card_id)
            
            if outcome == 'easy':
                card.move_forward() # Move to next box (review later)
            elif outcome == 'hard':
                card.reset_progress() # Reset to box 1 (review sooner)
            elif outcome == 'medium':
                # Maybe keep in same box but update review time? 
                # For simplicity, treat as slight forward or stay. 
                # Let's just update last_reviewed but not move box widely.
                card.last_reviewed_at = timezone.now()
                card.save()

            # --- ANALYTICS LOGGING ---
            if request.user.is_authenticated:
                ActivityLog.objects.create(
                    user=request.user,
                    app_name='flashcard',
                    activity_type='card_reviewed',
                    topic=card.deck.title,
                    metadata={'deck_id': str(card.deck.id), 'outcome': outcome}
                )
            # -------------------------

            return JsonResponse({"status": "success", "new_box": card.box})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
def explain_card_api(request, card_id):
    if request.method == "POST":
        try:
            card = get_object_or_404(Flashcard, id=card_id)
            
            # Check if we already have one cached
            if card.explanation:
                return JsonResponse({"explanation": card.explanation})
            
            # Generate new
            explanation = explain_card_content(card.front, card.back)
            
            # Save it
            card.explanation = explanation
            card.save()
            
            return JsonResponse({"explanation": explanation})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
def delete_card_api(request, card_id):
    if request.method == "DELETE":
        try:
            card = get_object_or_404(Flashcard, id=card_id)
            card.delete()
            return JsonResponse({"status": "success", "message": "Flashcard deleted successfully."})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
def delete_deck_api(request, deck_id):
    if request.method == "DELETE":
        try:
            deck = get_object_or_404(FlashcardDeck, id=deck_id)
            deck.delete()
            return JsonResponse({"status": "success", "message": "Deck deleted successfully."})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
def generate_quiz_view(request, deck_id):
    """
    Generates a quiz from the deck and renders the quiz page.
    """
    deck = get_object_or_404(FlashcardDeck, id=deck_id)
    
    if request.method == "POST":
        # Generate new quiz data
        cards = list(deck.cards.all().values('front', 'back'))
        quiz_data = generate_quiz_from_cards(cards)
        
        # Store in session or pass to context (Context is easier for simple flow)
        # We'll render a template with the JSON data embedded
        return render(request, "flashcard_generator/quiz.html", {
            "deck": deck, 
            "quiz_data": json.dumps(quiz_data)
        })
        
    return JsonResponse({"error": "Use POST to generate quiz"}, status=405)

@csrf_exempt
def submit_quiz_api(request):
    """
    Logs the quiz score.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            deck_id = data.get("deck_id")
            score = data.get("score")
            total = data.get("total")
            
            if request.user.is_authenticated:
                deck = get_object_or_404(FlashcardDeck, id=deck_id)
                ActivityLog.objects.create(
                    user=request.user,
                    app_name='flashcard',
                    activity_type='quiz_completed',
                    topic=deck.title,
                    score=score,
                    metadata={'deck_id': str(deck_id), 'total': total},
                    completed=True
                )
                
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
def generate_from_unit(request, unit_id):
    """Generates a flashcard deck directly from a Course Unit."""
    unit = get_object_or_404(CourseUnit, id=unit_id)
    
    # Use localized course_id for RAG
    course_id = unit.course.id

    # Call AI Service with unit title as initial query hint
    cards_data = generate_flashcards(input_text=unit.title, course_id=course_id)
    
    if not cards_data:
        # Fallback to general unit context extraction if RAG search is empty
        # (This handles newly created units without embeddings yet)
        from course.services.context_provider import get_course_context
        context_text = get_course_context(request.user, course_id)
        if context_text:
            cards_data = generate_flashcards(input_text=context_text[:5000])

    if not cards_data:
        return redirect('course:unit_detail', unit_id=unit.id)
        
    # ... existing deck creation logic ...
        
    # Create Deck linked to Unit
    deck = FlashcardDeck.objects.create(
        title=f"Revise: {unit.title}",
        unit=unit,
        difficulty="Medium"
    )
    
    for card in cards_data:
        if 'front' in card and 'back' in card:
            Flashcard.objects.create(
                deck=deck,
                front=card['front'],
                back=card['back'],
                exam_tip=card.get('exam_tip', "")
            )
            
    # Log Activity
    if request.user.is_authenticated:
        ActivityLog.objects.create(
            user=request.user,
            app_name='flashcard',
            activity_type='deck_generated',
            topic=deck.title,
            metadata={'deck_id': str(deck.id), 'source': 'course_unit'}
        )

    return redirect('flashcard_generator:study_deck', deck_id=deck.id)

@csrf_exempt
def generate_from_course(request, course_id):
    """Generates a flashcard deck from the Course context using RAG."""
    course = get_object_or_404(Course, id=course_id)
    
    # Call AI Service with course title as query hint
    cards_data = generate_flashcards(input_text=course.title, course_id=course.id)
    
    if not cards_data:
        # Fallback to general course context if RAG search is empty
        context_text = CourseContextEngine.get_course_context(course.id)
        if context_text:
            cards_data = generate_flashcards(input_text=context_text[:5000])

    if not cards_data:
        # 5. Robust Parsing
        # The `cards_data` variable is already the result of `generate_flashcards`,
        # which should handle robust parsing and return an error message if generation fails.
        # So, if `cards_data` is empty here, it means no valid cards were generated.
        print(f"Gen: LLM returned empty or invalid response for Course {course_id}.")
        # The `generate_flashcards` function should ideally return a list with an error dict
        # if it fails, or an empty list if no cards were generated but no error occurred.
        # If it returns an empty list, we redirect. If it returns an error dict, we should handle it.
        # For now, assuming an empty list means no cards, so redirect.
        return redirect('course:course_dashboard', course_id=course.id)
        
    # ... rest of the logic ...
        
    # Create Deck linked to Course
    deck = FlashcardDeck.objects.create(
        title=f"Mastery: {course.title}",
        course=course,
        difficulty="Medium"
    )
    
    for card in cards_data:
        if 'front' in card and 'back' in card:
            Flashcard.objects.create(
                deck=deck,
                front=card['front'],
                back=card['back'],
                exam_tip=card.get('exam_tip', "")
            )
            
    # Log Activity & Session
    from course.models import StudySession
    if request.user.is_authenticated:
        ActivityLog.objects.create(
            user=request.user,
            app_name='flashcard',
            activity_type='deck_generated',
            topic=deck.title,
            metadata={'deck_id': str(deck.id), 'source': 'course_full'}
        )
        StudySession.objects.create(
            user=request.user,
            course=course,
            activity_type='flashcards',
            time_spent=5 # Initial credits
        )

    return redirect('flashcard_generator:study_deck', deck_id=deck.id)

@login_required
def dynamic_flashcards_view(request, course_id=None):
    """
    Renders the flashcard study page for a course using dynamic generation.
    """
    if course_id:
        course = get_object_or_404(Course, id=course_id)
        # Ensure it's active in session
        request.session['active_course_id'] = course.id
    else:
        course = ActiveCourseManager.get_active_course(request)
    
    if not course:
        return redirect('course:course_list')
        
    return render(request, "flashcard_generator/flashcards_dynamic.html", {
        'course': course
    })

@csrf_exempt
def get_dynamic_flashcards_api(request, course_id):
    """
    API endpoint for getting dynamic flashcards.
    """
    logger.info(f"API: get_dynamic_flashcards_api called for Course {course_id}")
    course = get_object_or_404(Course, id=course_id)
    
    # 10-minute cache is handled inside generate_flashcards_dynamic
    try:
        cards = generate_flashcards_dynamic(request.user, course.id)
        logger.info(f"API: Flashcards generated successfully for Course {course_id}. Count: {len(cards)}")
    except Exception as e:
        logger.error(f"API: Error generating flashcards for Course {course_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        cards = [{"error": "An internal server error occurred during generation."}]
    
    return JsonResponse({
        "course_title": course.title,
        "cards": cards
    })

@csrf_exempt
def regenerate_flashcards_api(request, course_id):
    """
    Forces regeneration of flashcards by clearing cache.
    """
    logger.info(f"API: regenerate_flashcards_api called for Course {course_id}")
    course = get_object_or_404(Course, id=course_id)
    cache_key = f"flashcards_session_{request.user.id}_{course.id}"
    cache.delete(cache_key)
    
    try:
        cards = generate_flashcards_dynamic(request.user, course.id)
        logger.info(f"API: Flashcards regenerated successfully for Course {course_id}")
    except Exception as e:
        logger.error(f"API: Error regenerating flashcards for Course {course_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        cards = [{"error": "An internal server error occurred during regeneration."}]
    
    return JsonResponse({
        "status": "success",
        "cards": cards
    })
