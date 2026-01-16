import json
import re

try:
    import ollama
except ImportError:
    ollama = None


def generate_questions(topic="Python", level="beginner"):

    if ollama is None:
        return fallback_questions()

    prompt = f"""
ONLY return valid JSON.
NO explanation.
NO extra text.

Generate 5 multiple-choice questions for {topic} at {level} level.

JSON format:
[
  {{
    "question": "Question text",
    "options": ["A", "B", "C", "D"],
    "answer": "A"
  }}
]
"""

    try:
        response = ollama.chat(
            model="llama3.2:1b",
            messages=[{"role": "user", "content": prompt}]
        )

        text = response["message"]["content"].strip()
        match = re.search(r"\[.*\]", text, re.DOTALL)

        if not match:
            return fallback_questions()

        raw_questions = json.loads(match.group())

        # 🔒 HARD VALIDATION (IMPORTANT)
        clean_questions = []
        for q in raw_questions:
            if (
                "question" in q
                and "options" in q
                and "answer" in q
                and q["answer"] in q["options"]
            ):
                clean_questions.append(q)

        return clean_questions[:5] if clean_questions else fallback_questions()

    except Exception:
        return fallback_questions()


def generate_feedback(score, total, wrong_topics):

    percentage = (score / total) * 100 if total > 0 else 0

    if percentage >= 80:
        advice = "Excellent work! Keep practicing advanced problems."
    elif percentage >= 50:
        advice = "Good effort! Revise the basics and try again."
    else:
        advice = "Don't worry 😊 Start with fundamentals and practice daily."

    if ollama is None:
        return advice

    prompt = f"""
Give very short, friendly feedback (max 4 lines).
Simple English.

Score: {score}/{total}
Weak topics: {wrong_topics}
"""

    try:
        response = ollama.chat(
            model="llama3.2:1b",
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"].strip()
    except Exception:
        return advice


def explain_answer(question, correct_answer, user_answer):

    if ollama is None:
        return f"The correct answer is '{correct_answer}'."

    prompt = f"""
Question: {question}
Correct Answer: {correct_answer}
Student Answer: {user_answer}

Explain briefly why the correct answer is right.
"""

    try:
        response = ollama.chat(
            model="llama3.2:1b",
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"].strip()
    except Exception:
        return f"The correct answer is '{correct_answer}'."


def fallback_questions():
    return [
        {
            "question": "What is Python?",
            "options": ["A snake", "A programming language", "A browser", "A game"],
            "answer": "A programming language"
        },
        {
            "question": "Which keyword is used to define a function in Python?",
            "options": ["func", "define", "def", "function"],
            "answer": "def"
        },
        {
            "question": "Which data type is mutable?",
            "options": ["tuple", "string", "list", "int"],
            "answer": "list"
        },
        {
            "question": "Which symbol is used for comments in Python?",
            "options": ["//", "#", "/* */", "--"],
            "answer": "#"
        },
        {
            "question": "Which function outputs text in Python?",
            "options": ["echo()", "print()", "write()", "display()"],
            "answer": "print()"
        }
    ]
