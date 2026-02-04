
import os
import django
from django.conf import settings
import json
import logging

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from flashcard_generator.services.flashcard_ai import generate_quiz_from_cards

def reproduce_failure():
    print("Reproducing Quiz Failure with Data Structures content...")
    
    # Mock Flashcards (Data Structures theme)
    mock_cards = [
        {"front": "What is an array?", "back": "A collection of items stored at contiguous memory locations."},
        {"front": "What is a linked list?", "back": "A linear data structure where elements are not stored at contiguous memory locations."},
        {"front": "What is a stack?", "back": "A linear data structure which follows a particular order in which the operations are performed (LIFO)."},
        {"front": "What is a queue?", "back": "A linear structure which follows a particular order in which the operations are performed (FIFO)."},
        {"front": "What is a binary tree?", "back": "A tree data structure in which each node has at most two children."}
    ]
    
    print(f"Input Cards: {len(mock_cards)}")
    
    try:
        quiz = generate_quiz_from_cards(mock_cards)
        print(f"\nGenerered Quiz Items: {len(quiz)}")
        
        if len(quiz) == 0:
            print("FAILURE: No quiz items generated.")
        else:
            print("SUCCESS: Quiz items generated.")
            print(json.dumps(quiz[:1], indent=2)) # Print first item
            
    except Exception as e:
        print(f"\nERROR: {e}")

if __name__ == "__main__":
    reproduce_failure()
