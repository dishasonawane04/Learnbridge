from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from .models import QuizAttempt
from core.models import UserActivity
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
    """Generate quiz questions using Ollama with strict system prompt."""
    
    from course.services.ai_context import get_system_prompt

    system_prompt = ""
    if course and unit:
        system_prompt = get_system_prompt(course, unit)
    else:
        system_prompt = "SYSTEM:\nYou are an academic AI assistant."

    task_prompt = f"""TASK:
Generate {num_questions} multiple choice quiz questions about {subject} based strictly on the provided context/syllabus.

Format each question EXACTLY like this:
Q: [Question text]
A) [Option 1]
B) [Option 2]
C) [Option 3]
D) [Option 4]
ANSWER: [A, B, C, or D]

Make questions practical and relevant based on the context provided. Ensure each question has exactly 4 options and a clear correct answer."""

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
        
        if len(questions) < num_questions:
            return get_fallback_questions(subject, num_questions)
        
        return questions[:num_questions]
    
    except Exception as e:
        print(f"Error generating questions: {e}")
        return get_fallback_questions(subject, num_questions)

def parse_questions(text):
    """Parse AI-generated questions into structured format"""
    questions = []
    blocks = text.split('\n\n')
    
    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) < 6:
            continue
        
        question_text = ""
        options = []
        correct_answer = ""
        
        for line in lines:
            if line.startswith('Q:') or line.startswith('Question'):
                question_text = line.split(':', 1)[1].strip()
            elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                options.append(line[3:].strip())
            elif 'ANSWER:' in line.upper():
                answer_letter = line.split(':')[1].strip().upper()[0]
                answer_index = ord(answer_letter) - ord('A')
                if 0 <= answer_index < len(options):
                    correct_answer = options[answer_index]
        
        if question_text and len(options) == 4 and correct_answer:
            questions.append({
                "question": question_text,
                "options": options,
                "answer": correct_answer
            })
    
    return questions

def get_fallback_questions(subject, num=5):
    """Fallback questions when AI generation fails"""
    fallback_pool = {
        "Python": [
            {
                "question": "What is the output of: print(type([]))?",
                "options": ["<class 'list'>", "<class 'dict'>", "<class 'tuple'>", "<class 'set'>"],
                "answer": "<class 'list'>"
            },
            {
                "question": "Which keyword is used to create a function in Python?",
                "options": ["def", "function", "func", "define"],
                "answer": "def"
            },
            {
                "question": "What does the len() function do?",
                "options": ["Returns the length of an object", "Creates a new list", "Deletes an item", "Sorts a list"],
                "answer": "Returns the length of an object"
            },
            {
                "question": "Which operator is used for exponentiation in Python?",
                "options": ["**", "^", "//", "%%"],
                "answer": "**"
            },
            {
                "question": "What is the correct file extension for Python files?",
                "options": [".py", ".python", ".pt", ".pyt"],
                "answer": ".py"
            }
        ],
        "Machine Learning": [
            {
                "question": "What does ML stand for?",
                "options": ["Machine Learning", "Multiple Learning", "Manual Learning", "Model Learning"],
                "answer": "Machine Learning"
            },
            {
                "question": "Which algorithm is used for classification?",
                "options": ["Decision Tree", "K-Means", "PCA", "Apriori"],
                "answer": "Decision Tree"
            },
            {
                "question": "What is overfitting?",
                "options": ["Model performs well on training but poor on test data", "Model performs poorly on all data", "Model is too simple", "Model has no bias"],
                "answer": "Model performs well on training but poor on test data"
            },
            {
                "question": "Which library is commonly used for ML in Python?",
                "options": ["scikit-learn", "Django", "Flask", "Requests"],
                "answer": "scikit-learn"
            },
            {
                "question": "What is a neural network?",
                "options": ["A computing system inspired by biological neural networks", "A type of database", "A web framework", "A sorting algorithm"],
                "answer": "A computing system inspired by biological neural networks"
            }
        ]
    }
    
    pool = fallback_pool.get(subject, fallback_pool["Python"])
    return random.sample(pool, min(num, len(pool)))

def subjects_view(request):
    """Display subject selection page"""
    return render(request, 'quiz/subjects.html', {'subjects': SUBJECTS})

def quiz_view(request):
    """Main quiz view"""
    subject = request.GET.get('subject', 'Python')
    
    if request.method == 'POST':
        # Process quiz submission
        questions = request.session.get('questions', [])
        score = 0
        results = []
        
        for i, q in enumerate(questions):
            user_answer = request.POST.get(f'q{i}', '').strip()
            correct = user_answer == q['answer']
            if correct:
                score += 1
            
            results.append({
                'question': q['question'],
                'user_answer': user_answer or 'Not answered',
                'correct_answer': q['answer'],
                'is_correct': correct,
                'options': q['options']
            })
        
        total = len(questions)
        percentage = (score / total * 100) if total > 0 else 0
        
        if request.user.is_authenticated:
            UserActivity.objects.create(
                user=request.user,
                app_name='quiz',
                topic=subject,
                input_type='text',
                time_spent=120, # Estimated average time
                quiz_score=int(percentage),
                outcome='completed' if percentage >= 70 else 'needs_revision'
            )
        
        # Save attempt
        QuizAttempt.objects.create(
            subject=subject,
            score=score,
            total=total,
            percentage=percentage
        )
        
        return render(request, 'quiz/result.html', {
            'subject': subject,
            'score': score,
            'total': total,
            'percentage': percentage,
            'results': results,
            'passed': percentage >= 70
        })
    
    # Generate new questions
    from course.models import Course, CourseUnit
    course_id = request.GET.get('course_id')
    unit_id = request.GET.get('unit_id')
    
    course_obj = None
    unit_obj = None
    
    if course_id:
        from django.shortcuts import get_object_or_404
        course_obj = get_object_or_404(Course, id=course_id)
    
    if unit_id:
        from django.shortcuts import get_object_or_404
        unit_obj = get_object_or_404(CourseUnit, id=unit_id)
        if not course_obj:
            course_obj = unit_obj.course

    questions = async_to_sync(generate_quiz_questions)(subject, 5, course=course_obj, unit=unit_obj)
    request.session['questions'] = questions
    
    return render(request, 'quiz/quiz.html', {
        'subject': subject,
        'questions': questions,
        'course_id': course_id
    })

def start_unit_quiz(request, unit_id):
    """Initializes a quiz from a Course Unit."""
    from course.models import CourseUnit
    from django.shortcuts import get_object_or_404
    unit = get_object_or_404(CourseUnit, id=unit_id)
    
    # We default to 'Machine Learning' or 'Python' based on content or just pick one
    # For now, let's use the unit title as the 'subject' or just a generic placeholder
    # that the generator will use to influence the prompt.
    subject = unit.title
    
    return redirect(f"{reverse('quiz:quiz_start')}?unit_id={unit.id}&subject={subject}")
