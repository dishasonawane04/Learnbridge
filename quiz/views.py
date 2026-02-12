from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from .models import QuizAttempt
from core.models import UserActivity
from course.models import Course, CourseUnit
from course.services.state import ActiveCourseManager
from core.ai.services import CourseContextEngine
import ollama
import json
import random
import asyncio
from asgiref.sync import async_to_sync

SUBJECTS = [
    {"key": "Python", "name": "Python Programming", "icon": "fab fa-python"},
    {"key": "Machine Learning", "name": "Machine Learning", "icon": "fas fa-brain"},
    {"key": "Data Science", "name": "Data Science", "icon": "fas fa-chart-bar"},
    {"key": "Web Development", "name": "Web Development", "icon": "fas fa-code"},
    {"key": "Database", "name": "Database & SQL", "icon": "fas fa-database"},
    {"key": "Cloud Computing", "name": "Cloud Computing", "icon": "fas fa-cloud"},
]

async def generate_quiz_questions(subject, num_questions=5, course=None, unit=None):
    """Generate mixed quiz questions (MCQ, T/F, Short) using CourseContext."""
    
    context_text = ""
    if course:
        context_text = CourseContextEngine.get_course_context(course.id)
    elif unit:
        context_text = CourseContextEngine.get_course_context(unit.course.id)
    
    if not context_text:
        return []

    system_prompt = (
        "You are an academic examiner for LearningBridge AI. "
        "Your task is to generate a challenging quiz based STRICTLY on the provided course material. "
        f"\n--- COURSE CONTENT ---\n{context_text}\n-----------------\n"
    )

    task_prompt = f"""Generate {num_questions} questions about {subject}.
Include a mix of:
1. Multiple Choice (4 options)
2. True/False
3. Short Answer (Single sentence or phrase)

Format each question EXACTLY like this:
TYPE: [MCQ / TF / SHORT]
Q: [Question text]
A: [Option A / True / NA]
B: [Option B / False / NA]
C: [Option C / NA / NA]
D: [Option D / NA / NA]
ANSWER: [Correct Option or Short Answer Text]

Ensure every question follows this 7-line format strictly for parsing."""

    final_prompt = f"{system_prompt}\n\n{task_prompt}"

    try:
        client = ollama.AsyncClient()
        response = await client.chat(
            model=settings.OLLAMA_MODEL_TEXT,
            messages=[{"role": "user", "content": final_prompt}],
            options={"temperature": 0.7}
        )
        
        text = response["message"]["content"]
        questions = parse_questions(text)
        
        return questions
    
    except Exception as e:
        print(f"Error generating questions: {e}")
        return []

def parse_questions(text):
    """Parse AI-generated mixed-type questions"""
    questions = []
    blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
    
    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) < 4: continue
        
        q_data = {
            "type": "MCQ",
            "question": "",
            "options": [],
            "answer": ""
        }
        
        for line in lines:
            if line.startswith('TYPE:'):
                q_data["type"] = line.split(':')[1].strip().upper()
            elif line.startswith('Q:'):
                q_data["question"] = line.split(':', 1)[1].strip()
            elif line.startswith(('A:', 'B:', 'C:', 'D:')):
                val = line.split(':', 1)[1].strip()
                if val != "NA":
                    q_data["options"].append(val)
            elif line.startswith('ANSWER:'):
                q_data["answer"] = line.split(':', 1)[1].strip()
        
        if q_data["question"] and q_data["answer"]:
            questions.append(q_data)
            
    return questions

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
        
        # Save attempt with Course link
        QuizAttempt.objects.create(
            user=request.user if request.user.is_authenticated else None,
            course=active_course,
            subject=subject,
            score=score,
            total=total,
            percentage=percentage,
            generated_questions=questions
        )
        
        return render(request, 'quiz/result.html', {
            'subject': subject,
            'score': score,
            'total': total,
            'percentage': percentage,
            'results': results,
            'passed': percentage >= 70,
            'course': active_course
        })
    
    # Generate questions based on Active Course
    questions = async_to_sync(generate_quiz_questions)(subject, 5, course=active_course)
    request.session['questions'] = questions
    
    return render(request, 'quiz/quiz.html', {
        'subject': subject,
        'questions': questions,
        'course': active_course
    })

def start_unit_quiz(request, unit_id):
    """Legacy entry point, redirects to session-aware quiz"""
    unit = get_object_or_404(CourseUnit, id=unit_id)
    ActiveCourseManager.set_active_course(request, unit.course.id)
    return redirect(f"{reverse('quiz:quiz_start')}?subject={unit.title}")
