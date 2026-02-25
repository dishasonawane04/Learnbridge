import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from django.contrib.auth.models import User
from course.models import Course
from flashcard_generator.services.dynamic_gen import generate_flashcards_dynamic
from flashcard_generator.models import StudentFlashcardHistory

def diagnose_empty_cards(course_id):
    user = User.objects.first()
    course = Course.objects.get(id=course_id)
    
    print(f"--- DIAGNOSING COURSE {course_id}: {course.title} ---")
    print(f"Materials Count: {course.course_materials.count()}")
    print(f"Text Length: {len(course.extracted_text or '')}")
    
    history_count = StudentFlashcardHistory.objects.filter(student=user, course=course).count()
    print(f"History Entries for User {user.id}: {history_count}")
    
    # Run the generator
    cards = generate_flashcards_dynamic(user, course_id)
    
    print(f"Generation Result: {len(cards)} cards")
    if len(cards) == 1 and "error" in cards[0]:
        print(f"Error returned: {cards[0]['error']}")
    elif len(cards) == 0:
        print("Empty list returned. Checking if it's due to duplicates...")
        # We can't easily check inside without more prints, but if history is large, it's likely.
    else:
        print("Success! Generated cards.")

if __name__ == "__main__":
    import sys
    cid = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    diagnose_empty_cards(cid)
