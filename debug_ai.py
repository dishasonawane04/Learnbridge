
import os
import django
import sys
from pathlib import Path

# Setup Django environment
sys.path.append(r'd:\DISHA\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from flashcard_generator.ai_logic import generate_flashcards, explain_card_content

print("--- Testing Flashcard Generation ---")
try:
    text = "Mitochondria is the powerhouse of the cell."
    cards = generate_flashcards(input_text=text, difficulty="Easy")
    print(f"Success! Generated {len(cards)} cards.")
    print(cards)
except Exception as e:
    print(f"GENERATION FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n--- Testing Explanation ---")
try:
    expl = explain_card_content("Mitochondria", "Powerhouse of the cell")
    print(f"Explanation: {expl}")
except Exception as e:
    print(f"EXPLANATION FAILED: {e}")
