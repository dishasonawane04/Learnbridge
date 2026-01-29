import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from flashcard_generator.services.flashcard_ai import generate_flashcards

def test_generation():
    print("Testing Flashcard Generation (Advanced)...")
    text = (
        "The CRISPR-Cas9 system functions as an adaptive immune mechanism in bacteria, utilizing RNA-guided DNA cleavage. "
        "Upon viral infection, short viral DNA sequences are integrated into the host's CRISPR locus as 'spacers'. "
        "These are transcribed into pre-crRNA and processed into mature crRNA, which forms a complex with the Cas9 endonuclease. "
        "The crRNA guides Cas9 to the target viral DNA by base-pairing with the protospacer sequence, strictly requiring a downstream Protospacer Adjacent Motif (PAM). "
        "Binding induces a conformational change in Cas9, activating its HNH and RuvC domains to generate a double-strand break (DSB). "
        "In eukaryotic gene editing, this DSB is repaired via Non-Homologous End Joining (NHEJ), which is error-prone, or Homology-Directed Repair (HDR), allowing precise edits."
    )
    
    print(f"Input: {text[:100]}...")
    try:
        cards = generate_flashcards(input_text=text, difficulty="Medium")
        print(f"\nGenerated {len(cards)} cards:")
        for i, card in enumerate(cards):
            print(f"{i+1}. Q: {card.get('front')} | A: {card.get('back')}")
            if card.get('exam_tip'):
                print(f"   Tip: {card.get('exam_tip')}")
            
        if len(cards) > 0:
            print("\nSUCCESS: Flashcards generated.")
        else:
            print("\nFAILURE: No cards generated.")
            
    except Exception as e:
        print(f"\nERROR: {e}")

if __name__ == "__main__":
    test_generation()
