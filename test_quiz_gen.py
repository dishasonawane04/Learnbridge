import os
import django
from django.conf import settings
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from flashcard_generator.services.flashcard_ai import generate_quiz_from_cards

def test_quiz_generation():
    print("Testing Quiz Generation...")
    
    # Mock Flashcards
    mock_cards = [
        {"front": "What is Python?", "back": "A high-level programming language."},
        {"front": "What is a list?", "back": "A mutable, ordered sequence of elements."},
        {"front": "What is a tuple?", "back": "An immutable, ordered sequence of elements."}
    ]
    
    print(f"Input Cards: {len(mock_cards)}")
    
    try:
        quiz = generate_quiz_from_cards(mock_cards)
        print(f"\nGenerated Quiz Data ({type(quiz)}):")
        print(json.dumps(quiz, indent=2))
        
        if len(quiz) > 0:
            print("\nIterating...")
            for i, q in enumerate(quiz):
                print(f"\nQ{i+1}: {q.get('question')}")
                print(f"   Options: {q.get('options')}")
                print(f"   Answer: {q.get('answer')}")
            print("\nSUCCESS: Quiz generated.")
        else:
            print("\nFAILURE: No questions generated.")
            
    except Exception as e:
        print(f"\nERROR: {e}")

if __name__ == "__main__":
    test_quiz_generation()
