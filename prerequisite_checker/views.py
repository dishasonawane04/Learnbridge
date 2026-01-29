from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import PrerequisiteSession, ConceptResult
from .ai_logic import get_prerequisites, generate_questions, evaluate_readiness
import json

@login_required
def topic_input_view(request):
    """
    Step 1: User enters a topic.
    """
    if request.method == "POST":
        topic = request.POST.get("topic")
        print(f"DEBUG: Topic Input: {topic}")
        if topic:
            # 1. Create Session
            session = PrerequisiteSession.objects.create(
                user=request.user,
                target_topic=topic
            )
            
            # 2. Get Prerequisites (Mock or AI)
            print("DEBUG: Calling AI for prerequisites...")
            prereqs = get_prerequisites(topic)
            print(f"DEBUG: Prerequisites found: {prereqs}")
            
            if not prereqs:
                # Handle failure gracefully
                print("DEBUG: No prerequisites returned.")
                # For now, just render with error (or could redirect with message)
                return render(request, "prerequisite_checker/input.html", {"error": "Could not identify prerequisites. Please try a more specific topic."})

            # 3. Generate Questions
            print("DEBUG: Generating questions...")
            questions = generate_questions(prereqs)
            print(f"DEBUG: Questions generated: {len(questions)}")
            
            if not questions:
                return render(request, "prerequisite_checker/input.html", {"error": "Could not generate diagnostic questions. Please try again."})

            # Store questions
            for item in questions:
                ConceptResult.objects.create(
                    session=session,
                    concept_name=item['concept'],
                    diagnostic_question=item['question'],
                    status='Pending'
                )
            
            print("DEBUG: Redirecting to quiz view")
            return redirect('prerequisite_checker:quiz_view', session_id=session.id)

    return render(request, "prerequisite_checker/input.html")

@login_required
def quiz_view(request, session_id):
    """
    Step 2: User answers diagnostic questions.
    """
    session = get_object_or_404(PrerequisiteSession, id=session_id, user=request.user)
    concepts = session.concept_results.all() # These have questions

    if request.method == "POST":
        # Collect answers
        responses_for_ai = []
        for concept in concepts:
            answer = request.POST.get(f"answer_{concept.id}")
            if answer:
                concept.user_answer = answer
                concept.save()
                responses_for_ai.append({
                    'concept': concept.concept_name,
                    'question': concept.diagnostic_question,
                    'answer': answer
                })
        
        # Evaluate
        evaluation = evaluate_readiness(responses_for_ai)
        
        # Update Session
        session.readiness_score = evaluation.get('score', 0)
        session.completed_at = timezone.now()
        session.save()
        
        # Update Concepts with feedback
        results = evaluation.get('results', [])
        for res in results:
            # Match by concept name
            concept_obj = concepts.filter(concept_name=res['concept']).first()
            if concept_obj:
                concept_obj.status = res['status']
                concept_obj.feedback = res['feedback']
                concept_obj.save()
                
        return redirect('prerequisite_checker:result_view', session_id=session.id)

    return render(request, "prerequisite_checker/quiz.html", {'session': session, 'concepts': concepts})

@login_required
def result_view(request, session_id):
    """
    Step 3: Show results.
    """
    session = get_object_or_404(PrerequisiteSession, id=session_id, user=request.user)
    concepts = session.concept_results.all()
    
    return render(request, "prerequisite_checker/results.html", {
        'session': session,
        'concepts': concepts
    })
