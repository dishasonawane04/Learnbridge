import os
import django
import sys

# Setup Django environment
sys.path.append('/Users/rajeevkumar/Learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from quiz.models import Question

def populate_questions():
    # 1. Python Questions (Scenario Based)
    questions = [
        {
            "text": "You are designing a system that needs to process a large stream of data where order doesn't matter, but you need to eliminate duplicates instantly. Which data structure is most appropriate?",
            "options": ["List", "Tuple", "Set", "Dictionary"],
            "correct_answer": "Set",
            "difficulty": "Proficient",
            "topic": "Python",
            "is_scenario_based": True,
            "explanation": "Sets are implemented as hash tables and provide O(1) average time complexity for lookups and insertion, making them ideal for duplicate elimination."
        },
        {
            "text": "Your code is raising a `KeyError` when accessing a dictionary. You want to provide a default value if the key doesn't exist, without using a try-except block. What is the pythonic way?",
            "options": ["dict[key]", "dict.get(key, default)", "if key in dict:", "dict.has_key(key)"],
            "correct_answer": "dict.get(key, default)",
            "difficulty": "Developing",
            "topic": "Python",
            "is_scenario_based": True,
            "explanation": "`dict.get()` returns None (or a specified default) if the key is missing, avoiding the crash."
        },
        {
            "text": "You have a list of 1 million integers. You need to verify if the number '42' exists in it multiple times. Which approach is fastest?",
            "options": ["Convert to Set then check", "Use '42 in list'", "Iterate with a for loop", "Sort the list first"],
            "correct_answer": "Convert to Set then check",
            "difficulty": "Advanced",
            "topic": "Python",
            "is_scenario_based": True,
            "explanation": "Looking up an item in a list is O(n), whereas in a set it is O(1). For repeated lookups, reducing to a set is much faster."
        },
        # 2. Data Science Questions
        {
            "text": "You are training a model to detect fraud (a rare event, 1 in 1000). Your model has 99.9% accuracy but catches 0 frauds. What metric should you have used instead of accuracy?",
            "options": ["Precision & Recall", "Mean Squared Error", "R-Squared", "Accuracy is fine"],
            "correct_answer": "Precision & Recall",
            "difficulty": "Proficient",
            "topic": "Data Science",
            "is_scenario_based": True,
            "explanation": "In imbalanced datasets, accuracy is misleading (a model that predicts 'Not Fraud' always will be 99.9% accurate). Precision and Recall (F1-score) are better."
        }
    ]

    for q_data in questions:
        Question.objects.get_or_create(
            text=q_data["text"],
            defaults={
                "options": q_data["options"],
                "correct_answer": q_data["correct_answer"],
                "difficulty": q_data["difficulty"],
                "topic": q_data["topic"],
                "is_scenario_based": True,
                "explanation": q_data["explanation"]
            }
        )
    
    print(f"Success: Added {len(questions)} scenario-based questions.")

if __name__ == "__main__":
    populate_questions()
