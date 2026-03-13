import os
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import ollama
from asgiref.sync import sync_to_async
from core.utils import log_activity
from .models import PracticeAttempt, PracticeQuestion, PracticeAnswer
from course.models import Course
from course.services.context_provider import get_course_context
import json

async def start_practice(request, course_id):
    course = await sync_to_async(get_object_or_404)(Course, id=course_id)
    
    # Generate Practice Questions using Context
    context_text = await sync_to_async(get_course_context)(request.user, course_id)
    
    system_prompt = (
        "You are an expert academic tutor. Generate a practice test based on the actual course notes provided below.\n"
        f"--- COURSE NOTES ---\n{context_text}\n---------------------\n"
    )
    
    task_prompt = """
    Generate exactly 3 Multiple Choice Questions (mcq) and exactly 2 Short Answer/Concept questions (short) based on the course notes.
    
    Output strictly in the following JSON format without any backticks, markdown, or extra text:
    {
      "questions": [
        {
          "type": "mcq",
          "question": "What is...?",
          "options": ["Option A", "Option B", "Option C", "Option D"],
          "answer": "Option A",
          "topic": "Topic Name"
        },
        {
          "type": "short",
          "question": "Explain the concept of...",
          "answer": "Detailed explanation...",
          "topic": "Topic Name"
        }
      ]
    }
    """
    
    client = ollama.AsyncClient()
    try:
        res = await client.chat(
            model=settings.OLLAMA_MODEL_TEXT,
            messages=[{'role': 'user', 'content': system_prompt + task_prompt}]
        )
        
        # Parse JSON
        raw_content = res['message']['content'].strip()
        if raw_content.startswith('```json'):
            raw_content = raw_content[7:-3].strip()
            
        data = json.loads(raw_content)
        
        # Save Attempt and Questions
        attempt = await sync_to_async(PracticeAttempt.objects.create)(
            user=request.user,
            course=course,
            total_questions=len(data['questions'])
        )
        
        for q in data['questions']:
            await sync_to_async(PracticeQuestion.objects.create)(
                attempt=attempt,
                q_type=q['type'],
                question_text=q['question'],
                options=q.get('options', []),
                correct_answer=q['answer'],
                topic=q.get('topic', 'General')
            )
            
        return redirect('assessment:attempt_practice', attempt_id=attempt.id)
        
    except Exception as e:
        # Fallback or error handling
        return await sync_to_async(render)(request, "assessment/practice_start.html", {"error": str(e), "course": course})


@sync_to_async
def get_attempt_and_questions(attempt_id):
    attempt = get_object_or_404(PracticeAttempt, id=attempt_id)
    questions = list(attempt.questions.all())
    return attempt, questions

async def attempt_practice(request, attempt_id):
    attempt, questions = await get_attempt_and_questions(attempt_id)
    return await sync_to_async(render)(request, "assessment/practice_test.html", {"attempt": attempt, "questions": questions})


async def submit_practice(request, attempt_id):
    if request.method == "POST":
        attempt, questions = await get_attempt_and_questions(attempt_id)
        
        total_score = 0
        weak_areas_dict = {}
        
        client = ollama.AsyncClient()
        
        for q in questions:
            user_ans = request.POST.get(f"q_{q.id}", "").strip()
            is_correct = False
            score_awarded = 0.0
            ai_exp = ""
            
            if q.q_type == 'mcq':
                if user_ans.lower() == q.correct_answer.lower():
                    is_correct = True
                    score_awarded = 1.0
                else:
                    ai_exp = f"The correct answer was {q.correct_answer}. Your answer was {user_ans}."
            else:
                # Grade short answer with AI
                eval_prompt = f"Question: {q.question_text}\nCorrect Answer/Concept: {q.correct_answer}\nStudent Answer: {user_ans}\n\nStrictly respond with a JSON object format like this without markdown:\n{{\"score\": 0.0 to 1.0, \"explanation\": \"Brief explanation mapping the student answer to correct concept\"}}"
                try:
                    res = await client.chat(
                        model=settings.OLLAMA_MODEL_TEXT,
                        messages=[{'role': 'user', 'content': eval_prompt}]
                    )
                    raw_content = res['message']['content'].strip()
                    if raw_content.startswith('```json'):
                        raw_content = raw_content[7:-3].strip()
                    
                    eval_data = json.loads(raw_content)
                    score_awarded = float(eval_data.get('score', 0))
                    ai_exp = eval_data.get('explanation', '')
                    if score_awarded > 0.7:
                        is_correct = True
                        
                except Exception as e:
                    ai_exp = str(e)
            
            total_score += score_awarded
            
            await sync_to_async(PracticeAnswer.objects.create)(
                attempt=attempt,
                question=q,
                user_answer=user_ans,
                is_correct=is_correct,
                score_awarded=score_awarded,
                ai_explanation=ai_exp
            )
            
            if not is_correct:
                weak_areas_dict[q.topic] = weak_areas_dict.get(q.topic, 0) + 1
        
        # Summarize
        attempt.score = total_score
        
        # Identify top weak areas
        weak_areas = [k for k, v in sorted(weak_areas_dict.items(), key=lambda item: item[1], reverse=True)]
        attempt.weak_areas = weak_areas[:3] # Top 3 weak areas
        
        recommendations = []
        if weak_areas:
            recommendations.append(f"Review notes on: {', '.join(attempt.weak_areas)}")
        if total_score / attempt.total_questions < 0.6:
            recommendations.append("Take a generated practice quiz to solidify basic concepts before attempting short answers.")
        else:
            recommendations.append("Great job! Consider using the Flashcards feature to maintain retention.")
            
        attempt.recommendations = recommendations
        
        await sync_to_async(attempt.save)()
        
        return redirect('assessment:practice_results', attempt_id=attempt.id)
    
    return redirect('assessment:attempt_practice', attempt_id=attempt_id)


async def practice_results(request, attempt_id):
    attempt = await sync_to_async(get_object_or_404)(PracticeAttempt, id=attempt_id)
    
    @sync_to_async
    def get_context(att):
        return {
            "attempt": att,
            "answers": list(att.answers.select_related('question').all()),
            "percentage": int((att.score / att.total_questions) * 100) if att.total_questions > 0 else 0
        }
        
    context = await get_context(attempt)
    return await sync_to_async(render)(request, "assessment/practice_results.html", context)


async def learning_support(request):
    response = None
    image_url = None
    topic = request.GET.get('topic', 'General Doubt')

    if request.method == "POST":
        doubt = request.POST.get("doubt")
        image = request.FILES.get("image")
        
        client = ollama.AsyncClient()

        from course.services.context_provider import get_course_context
        course_id = request.session.get("active_course_id") or request.GET.get('course_id')
        context = ""
        if course_id:
            context_text = await sync_to_async(get_course_context)(request.user, course_id=course_id)
            context = f"\nUse the following COURSE CONTEXT for reference:\n{context_text}\n"

        if image:
            def save_file(img):
                fs = FileSystemStorage()
                filename = fs.save(img.name, img)
                return fs.url(filename), fs.path(filename)
            
            image_url, image_path = await sync_to_async(save_file)(image)

            try:
                # Simplified LLaVA explanation for Learning Support
                res = await client.chat(
                    model=settings.OLLAMA_MODEL_VISION,
                    messages=[{
                        'role': 'user',
                        'content': f"Provide a simplified, step-by-step explanation for this doubt: {doubt or ''}. {context} Focus on clarity and basics.",
                        'images': [image_path]
                    }]
                )
                response = res['message']['content']
            except Exception as e:
                response = f"Error: {str(e)}"
        
        elif doubt:
            try:
                res = await client.chat(
                    model=settings.OLLAMA_MODEL_TEXT,
                    messages=[{
                        'role': 'user',
                        'content': f"Simplify this concept: {doubt}. {context} Use an analogy and a step-by-step breakdown."
                    }]
                )
                response = res['message']['content']
            except Exception as e:
                response = f"Error: {str(e)}"

        # Log Activity
        await sync_to_async(log_activity)(
            user=request.user,
            app_name="learning_support",
            topic=topic,
            input_type="image" if image else "text",
            time_spent=45,
            outcome="completed"
        )

    return await sync_to_async(render)(request, "assessment/learning_support.html", {
        "response": response,
        "image_url": image_url,
        "topic": topic
    })
