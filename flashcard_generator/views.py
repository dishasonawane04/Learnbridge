from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
import json
import os
from .models import FlashcardDeck, Flashcard
from .services.flashcard_ai import generate_flashcards, explain_card_content, generate_quiz_from_cards
from analytics.models import ActivityLog
from course.models import CourseUnit

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
    
    # Check if a deck already exists for this unit?
    existing_deck = FlashcardDeck.objects.filter(unit=unit).last()
         
    if not unit.content or len(unit.content) < 50:
        return redirect('course:unit_detail', unit_id=unit.id)

    # Call AI Service
    cards_data = generate_flashcards(input_text=unit.content, difficulty="Medium")
    
    if not cards_data:
        return redirect('course:unit_detail', unit_id=unit.id)
        
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
    """Generates a flashcard deck from the entire Course context."""
    from course.models import Course
    from core.ai.services import CourseContextEngine
    
    course = get_object_or_404(Course, id=course_id)
    
    # Get Full Context
    context_text = CourseContextEngine.get_course_context(course.id)
    
    if not context_text or len(context_text) < 50:
        return redirect('course:detail', course_id=course.id)

    # Call AI Service
    cards_data = generate_flashcards(input_text=context_text, difficulty="Medium")
    
    if not cards_data:
        return redirect('course:detail', course_id=course.id)
        
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
            
    # Log Activity
    if request.user.is_authenticated:
        ActivityLog.objects.create(
            user=request.user,
            app_name='flashcard',
            activity_type='deck_generated',
            topic=deck.title,
            metadata={'deck_id': str(deck.id), 'source': 'course_full'}
        )

    return redirect('flashcard_generator:study_deck', deck_id=deck.id)
