import os, sys, django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

# Enable logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from course.models import CourseMaterial, CourseNotes
from course.utils.extraction import extract_text_from_pdf
from core.ai.services import CourseContextEngine
import time

print("--- FULL REPROCESSING ---")
try:
    # Get the latest uploaded material
    m = CourseMaterial.objects.order_by('-id').first()
    print(f"Reprocessing Material ID {m.id}: {m.file.path}")
    
    # 1. Run the new OCR extraction
    text = extract_text_from_pdf(m.file.path)
    print(f"--- EXTRACTED TEXT LENGTH: {len(text)} ---")
    
    # 2. Save it to CourseMaterial
    m.extracted_text = text
    m.save(update_fields=['extracted_text'])
    
    # 3. Consolidate into CourseNotes
    CourseContextEngine.consolidate_course_notes(m.course.id)
    
    # 4. Clear Flashcard/Quiz Chunks so they regenerate properly
    from course.models import QuizChunk, FlashcardChunk
    QuizChunk.objects.filter(course_id=m.course.id).delete()
    FlashcardChunk.objects.filter(course_id=m.course.id).delete()
    
    # Verify it worked
    n = CourseNotes.objects.filter(course_id=m.course.id).first()
    print(f"--- FINAL COURSE {n.course.id} NOTES LENGTH: {len(n.extracted_text) if n and n.extracted_text else 0} ---")
    print("SUCCESS")

except Exception as e:
    print(f"Error: {e}")
