from django.shortcuts import render
from .ai_engine import generate_questions, generate_feedback, explain_answer
from .models import QuizAttempt


def home(request):
    subjects = [
        {"key": "Python", "name": "Python Programming"},
        {"key": "Math", "name": "Mathematics"},
        {"key": "Data Science", "name": "Data Science"},
    ]
    return render(request, "quiz/home.html", {"subjects": subjects})


def quiz(request):
    subject = request.GET.get("subject", "Python")

    # NEW QUIZ → clear old questions
    if request.method == "GET":
        request.session.pop("questions", None)

    if "difficulty" not in request.session:
        request.session["difficulty"] = "beginner"

    current_difficulty = request.session["difficulty"]

    if request.method == "GET":
        questions = generate_questions(subject, current_difficulty)
        request.session["questions"] = questions
    else:
        questions = request.session.get("questions", [])

    if request.method == "POST":
        score = 0
        results = []

        for i, q in enumerate(questions):
            user_ans = request.POST.get(f"q{i}", "").strip()
            correct_ans = q.get("answer", "").strip()

            is_correct = user_ans == correct_ans
            if is_correct:
                score += 1

            explanation = explain_answer(
                question=q["question"],
                correct_answer=correct_ans,
                user_answer=user_ans
            )

            results.append({
                "question": q["question"],
                "user_answer": user_ans or "Not Answered",
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "explanation": explanation
            })

        total = len(questions)
        percentage = (score / total) * 100 if total else 0

        feedback = generate_feedback(
            score=score,
            total=total,
            wrong_topics=[r["question"] for r in results if not r["is_correct"]]
        )

        next_level = get_next_difficulty(current_difficulty, score, total)
        request.session["difficulty"] = next_level

        QuizAttempt.objects.create(
            topic=subject,
            difficulty=current_difficulty,
            score=score,
            total=total,
            percentage=percentage
        )

        request.session.pop("questions", None)

        return render(request, "quiz/result.html", {
            "score": score,
            "total": total,
            "level": get_level(score, total),
            "next_level": next_level,
            "feedback": feedback,
            "results": results
        })

    return render(request, "quiz/quiz.html", {
        "questions": questions,
        "subject": subject,
        "difficulty": current_difficulty
    })


def get_level(score, total):
    if total == 0:
        return "Low"
    percentage = (score / total) * 100
    if percentage >= 80:
        return "High"
    elif percentage >= 50:
        return "Medium"
    return "Low"


def get_next_difficulty(current_difficulty, score, total):
    if total == 0:
        return current_difficulty

    percentage = (score / total) * 100

    if percentage < 50:
        return current_difficulty

    if current_difficulty == "beginner":
        return "amateur"
    if current_difficulty == "amateur":
        return "regular"
    if current_difficulty == "regular":
        return "professional"

    return "legend"
