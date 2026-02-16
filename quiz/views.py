from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from .models import QuizAttempt
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
from ai_engine.quiz_generator import generate_quiz

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
    """Main quiz view responsive to CourseContext"""
    subject = request.GET.get('subject', 'General')
    active_course = ActiveCourseManager.get_active_course(request)
    
    if request.method == 'POST':
        questions = request.session.get('questions', [])
        score = 0
        results = []
        
        for i, q in enumerate(questions):
            user_answer = request.POST.get(f'q{i}', '').strip()
            # Simple exact match for now, could be improved with AI grading for SHORT
            is_correct = user_answer.lower() == q['answer'].lower()
            if is_correct: score += 1
            
            results.append({
                'question': q['question'],
                'user_answer': user_answer or 'Not answered',
                'correct_answer': q['answer'],
                'is_correct': is_correct,
                'type': q.get('type', 'MCQ'),
                'options': q.get('options', [])
            })
        
        total = len(questions)
        percentage = (score / total * 100) if total > 0 else 0
        
        # Track history and weak areas
        used_chunk_ids = [q.get('chunk_id') for q in questions if q.get('chunk_id')]
        failed_topics = []
        for res in results:
            if not res['is_correct']:
                # Find the original question to get chunk metadata if possible
                failed_topics.append({
                    'question': res['question'],
                    'answer': res['correct_answer']
                })

        # Save attempt with History tracking (Feature 5) and progress reporting (Feature 7)
        QuizAttempt.objects.create(
            user=request.user if request.user.is_authenticated else None,
            course=active_course,
            subject=subject,
            score=score,
            total=total,
            percentage=percentage,
            generated_questions=questions,
            used_chunk_ids=used_chunk_ids,
            failed_topics=failed_topics
        )
        
        # Clear session after successful save
        if 'questions' in request.session:
            del request.session['questions']

        return render(request, 'quiz/result.html', {
            'subject': subject,
            'score': score,
            'total': total,
            'percentage': percentage,
            'results': results,
            'passed': percentage >= 70,
            'course': active_course,
            'failed_topics': failed_topics
        })
    
    questions = request.session.get('questions', [])
    
    # Validation: Ensure existing session questions have the new required keys
    if questions and (not isinstance(questions[0], dict) or 'correct_index' not in questions[0] or 'id' not in questions[0]):
        print("Outdated quiz session detected, clearing...")
        questions = []
        if 'questions' in request.session:
            del request.session['questions']
    
    # Generate questions based on Active Course
    if not questions:
        if active_course:
            # Step 7: Load Questions into Quiz Page
            questions = generate_quiz(active_course.id)
            if not questions:
                # Instead of a separate file, we'll render a template with an error message
                return render(request, 'quiz/quiz.html', {
                    'subject': subject,
                    'error_message': "No questions generated. Please ensure you have uploaded course material and it has been processed.",
                    'course': active_course
                })
        else:
            return redirect('quiz:quiz_subjects')
            
        request.session['questions'] = questions
    
    # Track which chunks are being used in this attempt
    # We will save these at the end of the attempt
    
    return render(request, 'quiz/quiz.html', {
        'subject': subject,
        'questions': questions,
        'course': active_course,
        'LETTERS': ['A', 'B', 'C', 'D', 'E']
    })

# Legacy explanation logic removed in favor of Step 8 (pre-generated reveal)

def start_unit_quiz(request, unit_id):
    """Legacy entry point, redirects to session-aware quiz"""
    unit = get_object_or_404(CourseUnit, id=unit_id)
    ActiveCourseManager.set_active_course(request, unit.course.id)
    return redirect(f"{reverse('quiz:quiz_start')}?subject={unit.title}")
