from django.shortcuts import render, redirect, get_object_or_404
import logging
from django.urls import reverse
from django.conf import settings
from .models import QuizAttempt, StudentAnswer, StudentQuestionHistory, Quiz, Question, Option
from core.models import UserActivity
from course.models import Course, CourseUnit
from course.services.state import ActiveCourseManager
from core.ai.services import CourseContextEngine
import json
import random
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .forms import ManualQuestionForm
from .utils.document_reader import get_course_text
from .utils.ollama_quiz import generate_mcq
from ai_engine.quiz_generator import generate_quiz, generate_quiz_stream
from django.http import StreamingHttpResponse
import asyncio
from asgiref.sync import sync_to_async
from ai_engine.utils.optimization import AIContextOptimizer
import time

logger = logging.getLogger(__name__)

SUBJECTS = [
    {"key": "Python", "name": "Python Programming", "icon": "fab fa-python"},
    {"key": "Machine Learning", "name": "Machine Learning", "icon": "fas fa-brain"},
    {"key": "Data Science", "name": "Data Science", "icon": "fas fa-chart-bar"},
    {"key": "Web Development", "name": "Web Development", "icon": "fas fa-code"},
    {"key": "Database", "name": "Database & SQL", "icon": "fas fa-database"},
    {"key": "Cloud Computing", "name": "Cloud Computing", "icon": "fas fa-cloud"},
]

# Legacy generation logic removed in favor of ai_engine pipeline

def get_fallback_questions(subject, num=5):
    """Fallback questions when AI generation fails"""
    fallback_pool = {
        "Python": [
            {"type": "MCQ", "question": "What is the output of: print(type([]))?", "options": ["<class 'list'>", "<class 'dict'>", "<class 'tuple'>", "<class 'set'>"], "answer": "<class 'list'>"},
            {"type": "MCQ", "question": "Which keyword is used to create a function in Python?", "options": ["def", "function", "func", "define"], "answer": "def"},
        ]
    }
    pool = fallback_pool.get(subject, fallback_pool["Python"])
    return random.sample(pool, min(num, len(pool)))

def subjects_view(request):
    """Display subject selection page"""
    return render(request, 'quiz/subjects.html', {'subjects': SUBJECTS})

def quiz_view(request):
    # Main quiz view responsive to CourseContext and course_id parameter
    active_course = ActiveCourseManager.get_active_course(request)
    
    if not active_course:
        return redirect('course:course_list')
        
    subject = request.GET.get('subject', active_course.title)
    
    if request.method == 'POST':
        # ... (POST handling remains same)
        questions = request.session.get('questions', [])
        score = 0
        results = []
        
        for i, q in enumerate(questions):
            user_answer = request.POST.get(f'q{i}', '').strip()
            # Simple exact match for now, could be improved with AI grading for SHORT
            is_correct = user_answer.lower() == q['answer'].lower() if 'answer' in q else (user_answer.lower() == q['correct_answer'].lower() if 'correct_answer' in q else False)
            if is_correct: score += 1
            
            results.append({
                'question': q['question'],
                'user_answer': user_answer or 'Not answered',
                'correct_answer': q.get('correct_answer') or q.get('answer'),
                'is_correct': is_correct,
                'type': q.get('type', 'MCQ'),
                'options': q.get('options', [])
            })
        
        total = len(questions)
        percentage = (score / total * 100) if total > 0 else 0
        
        # Save attempt
        QuizAttempt.objects.create(
            user=request.user if request.user.is_authenticated else None,
            course=active_course,
            subject=subject,
            score=score,
            total=total,
            percentage=percentage,
            generated_questions=questions
        )
        
        # Clear session after successful save
        if 'questions' in request.session:
            del request.session['questions']
        if 'quiz_course_id' in request.session:
            del request.session['quiz_course_id']

        return render(request, 'quiz/result.html', {
            'subject': subject,
            'score': score,
            'total': total,
            'percentage': percentage,
            'results': results,
            'passed': percentage >= 70,
            'course': active_course
        })
    
    questions = request.session.get('questions', [])
    session_course_id = request.session.get('quiz_course_id')
    
    # Only clear if it's a "fresher" click from a different course or if we explicitly want a new one
    # If questions already exist (e.g. from stream), Don't clear them!
    if not questions:
        if request.GET.get('course_id') or request.GET.get('subject') or (active_course and session_course_id != active_course.id):
            if 'questions' in request.session:
                del request.session['questions']
            questions = []
    
    # Generate fresh questions for new attempt
    if not questions:
        if active_course:
            # Render loading state first for streaming
            return render(request, 'quiz/quiz_loading.html', {
                'subject': subject,
                'course': active_course
            })
        else:
            return redirect('quiz:quiz_subjects')
    
    return render(request, 'quiz/quiz.html', {
        'subject': subject,
        'questions': questions,
        'course': active_course
    })

def quiz_stream_api(request, course_id):
    """
    Server-Sent Events (SSE) endpoint for streaming quiz questions.
    """
    course = get_object_or_404(Course, id=course_id)
    
    def stream_generator():
        try:
            # Requirement #1: Confirm document text exists
            from ai_engine.utils.optimization import AIContextOptimizer
            if not AIContextOptimizer.ensure_quiz_chunks(course_id):
                yield "data: {\"status\": \"error\", \"message\": \"No course material found. Please upload a document first.\"}\n\n"
                return

            # Requirement #3 & #4: Automatic Retry/Regeneration Loop
            max_stream_attempts = 2
            last_heartbeat = time.time()
            
            for stream_attempt in range(max_stream_attempts):
                questions = []
                context_used = ""
                
                try:
                    # Get context
                    context_used = AIContextOptimizer.get_next_quiz_chunk(course_id)
                    gen = generate_quiz_stream(course_id, user=request.user, num_questions=5)
                    
                    while True:
                        if time.time() - last_heartbeat > 15:
                            yield ": heartbeat\n\n"
                            last_heartbeat = time.time()
                        
                        try:
                            q = next(gen)
                            questions.append(q)
                            yield f"data: {json.dumps(q)}\n\n"
                        except StopIteration:
                            break
                        except Exception as e:
                            logger.error(f"Streaming token error: {e}")
                            break

                    if len(questions) >= 1:
                        if context_used:
                            AIContextOptimizer.mark_chunk_used(course_id, context_used)
                        yield "data: [DONE]\n\n"
                        return # Success
                    
                except Exception as e:
                    logger.warning(f"Quiz Stream Attempt {stream_attempt + 1} Error: {e}")
            
            # If all attempts fail
            yield "data: {\"status\": \"error\", \"message\": \"No questions were generated. Please check your document.\"}\n\n"
            
        except Exception as e:
            logger.error(f"Quiz Stream Error: {e}")
            yield f"data: {{\"status\": \"error\", \"message\": \"{str(e)}\"}}\n\n"

    response = StreamingHttpResponse(stream_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response

@csrf_exempt
def save_streamed_questions(request):
    """
    Saves questions collected by the frontend stream into the session.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            questions = data.get('questions', [])
            course_id = data.get('course_id')
            
            if questions and course_id:
                request.session['questions'] = questions
                request.session['quiz_course_id'] = course_id
                return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

@login_required
def user_courses_api(request):
    """
    Returns a list of courses for the current user.
    """
    courses = Course.objects.filter(user=request.user)
    data = [
        {"id": c.id, "title": c.title, "code": c.course_code, "category": c.category}
        for c in courses
    ]
    return JsonResponse(data, safe=False)


# Legacy explanation logic removed in favor of Step 8 (pre-generated reveal)

def start_unit_quiz(request, unit_id):
    """Legacy entry point, redirects to session-aware quiz"""
    unit = get_object_or_404(CourseUnit, id=unit_id)
    ActiveCourseManager.set_active_course(request, unit.course.id)
    return redirect(f"{reverse('quiz:quiz_start')}?subject={unit.title}")

@login_required
def generate_quiz_view(request, course_id):
    """View for faculty to generate a quiz from course materials using Ollama."""
    # Check if user is faculty/staff using account_profile
    is_faculty = request.user.is_staff or (hasattr(request.user, 'account_profile') and request.user.account_profile.role == 'Faculty')
    if not is_faculty:
        return redirect('course:course_dashboard', course_id=course_id)
        
    course = get_object_or_404(Course, id=course_id)
    text = get_course_text(course)
    
    if not text:
        # No material to generate from
        return redirect('course:course_dashboard', course_id=course_id)
        
    # Use the more robust generator from ai_engine
    ai_questions = generate_quiz(course.id)
    
    if not ai_questions:
        # AI failed to generate
        return redirect('course:course_dashboard', course_id=course_id)
        
    quiz = Quiz.objects.create(
        course=course,
        title=f"{course.title} AI Quiz"
    )
    
    for q in ai_questions:
        question_obj = Question.objects.create(
            quiz=quiz,
            question_text=q["question"],
            explanation=q.get("explanation", "")
        )
        
        for i, opt in enumerate(q["options"]):
            Option.objects.create(
                question=question_obj,
                option_text=opt,
                is_correct=(i == q["correct_index"])
            )
            
    return redirect('course:course_dashboard', course_id=course.id)

@login_required
def create_quiz_manual(request, course_id):
    """View for faculty to manually create quiz questions."""
    # Check if user is faculty/staff using account_profile
    is_faculty = request.user.is_staff or (hasattr(request.user, 'account_profile') and request.user.account_profile.role == 'Faculty')
    if not is_faculty:
        return redirect('course:course_dashboard', course_id=course_id)
        
    course = get_object_or_404(Course, id=course_id)
    # Ensure a manual quiz exists for this course
    quiz, created = Quiz.objects.get_or_create(
        course=course, 
        title=f"{course.title} Manual Quiz"
    )
    
    if request.method == 'POST':
        form = ManualQuestionForm(request.POST)
        if form.is_valid():
            q = Question.objects.create(
                quiz=quiz,
                question_text=form.cleaned_data["question"],
                explanation=form.cleaned_data.get("explanation", "")
            )
            
            options = [
                form.cleaned_data["option1"],
                form.cleaned_data["option2"],
                form.cleaned_data["option3"],
                form.cleaned_data["option4"],
            ]
            
            correct_idx = int(form.cleaned_data["correct_option"]) - 1
            
            for i, opt_text in enumerate(options):
                Option.objects.create(
                    question=q,
                    option_text=opt_text,
                    is_correct=(i == correct_idx)
                )
            # Redirect back to same page to add more questions or show success
            return redirect('quiz:create_quiz_manual', course_id=course_id)
    else:
        form = ManualQuestionForm()
        
    return render(request, "quiz/manual_quiz_form.html", {
        "form": form,
        "course": course,
        "quiz": quiz
    })

@login_required
def submit_quiz(request):
    """Refactored to handle dynamic session-based quiz attempts"""
    questions = request.session.get('questions', [])
    if not questions:
        return redirect('quiz:quiz_subjects')
    
    course_id = request.session.get('quiz_course_id')
    course = get_object_or_404(Course, id=course_id)
    
    score = 0
    total = len(questions)
    results = []
    
    # Create the attempt record early
    attempt = QuizAttempt.objects.create(
        user=request.user,
        course=course,
        subject=request.POST.get('subject', 'General Practice'),
        score=0, # Updated later
        total=total,
        percentage=0.0,
        accuracy=0.0,
        generated_questions=questions
    )
    
    for q in questions:
        q_id = q['id']
        selected_index = request.POST.get(f"question_{q_id}")
        
        is_correct = False
        user_answer = "Not answered"
        
        if selected_index is not None and selected_index != "":
            selected_index = int(selected_index)
            user_answer = q['options'][selected_index]
            if selected_index == q['correct_index']:
                score += 1
                is_correct = True
        
        correct_answer = q['options'][q['correct_index']]
        explanation = q.get('explanation', '')
        
        # Save per-question answer for analytics
        StudentAnswer.objects.create(
            attempt=attempt,
            question_text=q['question'],
            selected_option=user_answer,
            correct_option=correct_answer,
            is_correct=is_correct,
            explanation=explanation
        )
        
        # Record history for repetition prevention
        StudentQuestionHistory.objects.get_or_create(
            user=request.user,
            course=course,
            question_hash=q['hash']
        )
        
        results.append({
            'question': q['question'],
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct,
            'explanation': explanation,
            'type': 'MCQ',
            'options': q['options']
        })
        
    percentage = (score / total * 100) if total > 0 else 0
    
    # Update attempt summary
    attempt.score = score
    attempt.percentage = round(percentage, 2)
    attempt.accuracy = round(percentage, 2)
    attempt.save()
    
    # Clear session
    if 'questions' in request.session: del request.session['questions']
    if 'quiz_course_id' in request.session: del request.session['quiz_course_id']
    
    return render(request, "quiz/result.html", {
        "attempt": attempt,
        "score": score,
        "total": total,
        "percentage": round(percentage, 2),
        "results": results,
        "passed": percentage >= 70,
        "course": course,
        "subject": attempt.subject
    })
