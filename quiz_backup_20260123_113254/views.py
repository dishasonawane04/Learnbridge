from django.shortcuts import render, redirect
from django.conf import settings
from .ai_engine import generate_questions, generate_feedback, explain_answer
from .models import QuizAttempt, Question
from asgiref.sync import async_to_sync
import random

# STRICT DIFFICULTY LADDER
DIFFICULTY_LEVELS = ["Foundation", "Developing", "Proficient", "Advanced", "Mastery"]

def home(request):
    """
    Informational landing page.
    """
    return render(request, "quiz/home.html")

def subjects_view(request):
    """
    Subject selection page.
    """
    if request.GET.get('reset'):
        request.session.flush()

    subjects = [
        {"key": "Python", "name": "Python Programming", "icon": "🐍"},
        {"key": "Data Science", "name": "Data Science", "icon": "📊"},
        {"key": "Machine Learning", "name": "Machine Learning", "icon": "🤖"},
        {"key": "Full Stack", "name": "Full Stack Dev", "icon": "💻"},
        {"key": "Cloud", "name": "Cloud Computing", "icon": "☁️"},
        {"key": "Cybersecurity", "name": "Cybersecurity", "icon": "🔒"},
        {"key": "System Design", "name": "System Design", "icon": "🏗️"},
    ]
    return render(request, "quiz/subjects.html", {"subjects": subjects})

def quiz(request):
    """
    Main quiz view handling question generation, display, and scoring.
    """
    # 1. Subject Selection & Session setup
    subject = request.GET.get("subject", request.session.get("subject", "Python"))
    request.session["subject"] = subject

    # Use a subject-specific key for failed questions to prevent leakage
    failed_questions_key = f"failed_questions_{subject}"

    if "difficulty" not in request.session or request.session["difficulty"] not in DIFFICULTY_LEVELS:
        request.session["difficulty"] = "Foundation"
    
    current_difficulty = request.session["difficulty"]

    # 2. GET: Load or Generate Questions
    if request.method == "GET":
        
        # Check if we should start fresh (e.g. from Home page)
        if request.GET.get("start_new"):
            request.session["difficulty"] = "Foundation"
            request.session.pop(failed_questions_key, None)
            request.session.pop("questions", None)
            current_difficulty = "Foundation"
        
            # HYBRID GENERATION: DB First -> AI Fallback
            # 1. Try to get questions from DB
            db_questions_objs = list(Question.objects.filter(
                topic__icontains=subject, 
                difficulty=current_difficulty
            ).order_by('?')[:5])
            
            db_questions = []
            for q in db_questions_objs:
                db_questions.append({
                    "question": q.text,
                    "options": q.options,
                    "answer": q.correct_answer,
                    "explanation": q.explanation # Pass explanation for later
                })
            
            # 2. Calculate how many more we need
            num_needed = 5 - len(db_questions)
            
            ai_questions = []
            if num_needed > 0:
                # RETRY LOGIC for AI
                failed_questions = request.session.get(failed_questions_key, [])
                if failed_questions:
                    # If we have failed questions, use them first (max num_needed)
                    ai_questions = failed_questions[:num_needed]
                    # If still need more, generate
                    remaining = num_needed - len(ai_questions)
                    if remaining > 0:
                        generated = async_to_sync(generate_questions)(
                            topic=subject, 
                            level=current_difficulty, 
                            num_questions=remaining
                        )
                        ai_questions.extend(generated)
                else:
                    # Fresh AI generation
                    ai_questions = async_to_sync(generate_questions)(
                        topic=subject, 
                        level=current_difficulty, 
                        num_questions=num_needed
                    )
            
            # 3. Combine and Shuffle
            questions = db_questions + ai_questions
            # Deduplicate by question text to be safe
            seen_q = set()
            unique_questions = []
            for q in questions:
                if q["question"] not in seen_q:
                    unique_questions.append(q)
                    seen_q.add(q["question"])
            
            questions = unique_questions[:5] # Ensure max 5

            request.session["questions"] = questions
        
        else:
            questions = request.session["questions"]

        return render(request, "quiz/quiz.html", {
            "questions": questions,
            "subject": subject,
            "difficulty": current_difficulty,
            "difficulty_index": DIFFICULTY_LEVELS.index(current_difficulty) + 1 if current_difficulty in DIFFICULTY_LEVELS else 1,
            "total_levels": len(DIFFICULTY_LEVELS)
        })

    # 3. POST: Handle Submission
    if request.method == "POST":
        questions = request.session.get("questions", [])
        if not questions:
            return redirect('home')

        score = 0
        total = len(questions)
        wrong_questions_objects = []
        wrong_topics = []

        for i, q in enumerate(questions):
            user_ans = request.POST.get(f"q{i}", "").strip()
            correct_ans = q.get("answer", "").strip()
            if user_ans == correct_ans:
                score += 1
            else:
                wrong_questions_objects.append(q)
                wrong_topics.append(q["question"])

        percentage = (score / total) * 100 if total else 0
        passed = percentage >= 70

        # ADAPTIVE LOGIC
        next_difficulty = current_difficulty
        msg = ""
        if passed:
            msg = "Level Up! 🚀"
            curr_idx = DIFFICULTY_LEVELS.index(current_difficulty)
            if curr_idx < len(DIFFICULTY_LEVELS) - 1:
                next_difficulty = DIFFICULTY_LEVELS[curr_idx + 1]
            request.session.pop(failed_questions_key, None)
        else:
            msg = "Keep Trying! You'll get it."
            request.session[failed_questions_key] = wrong_questions_objects

        # Prepare AI tasks for parallel execution
        # Prepare AI tasks for parallel execution
        # Mix of pre-generated (DB) and real-time generation (AI)
        async def run_ai_tasks():
            explanation_tasks = []
            db_explanations = {} # Map index -> explanation text

            for i, q in enumerate(questions):
                user_ans = request.POST.get(f"q{i}", "").strip()
                
                # Check if we already have a curated explanation from DB
                if q.get("explanation"):
                    db_explanations[i] = q["explanation"]
                    # Add a dummy task to keep indices aligned or handle differently?
                    # Better: Add a None task and handle it later
                    explanation_tasks.append(None) 
                else:
                    explanation_tasks.append(explain_answer(
                        question=q["question"],
                        correct_answer=q.get("answer", "").strip(),
                        user_answer=user_ans
                    ))
            
            # Filter out None tasks for gather, but keep track of indices
            real_tasks = [t for t in explanation_tasks if t is not None]
            feedback_task = generate_feedback(score=score, total=total, wrong_topics=wrong_topics)
            
            # Run AI
            results = await asyncio.gather(*real_tasks, feedback_task)
            
            # Reconstruct list
            final_explanations = []
            task_idx = 0
            feedback_res = results[-1]
            ai_explanation_results = results[:-1]

            for i in range(len(questions)):
                if i in db_explanations:
                    final_explanations.append(db_explanations[i])
                else:
                    final_explanations.append(ai_explanation_results[task_idx])
                    task_idx += 1
            
            return final_explanations, feedback_res

        import asyncio
        explanations, feedback = async_to_sync(run_ai_tasks)()

        results = []
        for i, q in enumerate(questions):
            user_ans = request.POST.get(f"q{i}", "").strip()
            correct_ans = q.get("answer", "").strip()
            results.append({
                "question": q["question"],
                "user_answer": user_ans or "Not Answered",
                "correct_answer": correct_ans,
                "is_correct": user_ans == correct_ans,
                "explanation": explanations[i],
                "options": q.get("options", [])
            })

        # Update Session
        request.session["difficulty"] = next_difficulty
        # IMPORTANT: Clear current 'questions' so next GET generates new ones (or retries)
        request.session.pop("questions", None)

        # Save to DB
        QuizAttempt.objects.create(
            topic=subject,
            difficulty=current_difficulty,
            score=score,
            total=total,
            percentage=percentage
        )

        # Log Central Activity
        from core.utils import log_activity
        log_activity(
            user=request.user,
            app_name="quiz",
            topic=subject,
            input_type="text",
            time_spent=60, # Simplified for now
            quiz_score=int(percentage),
            outcome="completed" if passed else "needs_revision"
        )

        return render(request, "quiz/result.html", {
            "score": score,
            "total": total,
            "percentage": percentage,
            "passed": passed,
            "level": current_difficulty,
            "next_level": next_difficulty,
            "feedback": feedback,
            "results": results,
            "msg": msg
        })
