import re
import logging
from django.conf import settings
from core.ai.services import CourseContextEngine
from django.db import models
from course.models import CourseNotes, QuizChunk, FlashcardChunk

logger = logging.getLogger(__name__)

class AIContextOptimizer:
    """
    Unified optimizer for AI context (Quizzes, Flashcards, etc.)
    Ensures high performance by limiting input size.
    """
    
    @staticmethod
    def limit_text_size(text, max_words=2000):
        """
        If text > max_words, summarizes it to 800-1000 words.
        """
        words = text.split()
        if len(words) <= max_words:
            return text
            
        logger.info(f"AI Optimizer: Text too large ({len(words)} words). Summarizing...")
        
        prompt = (
            "Summarize the following educational content into approximately 800-1000 words. "
            "Focus on key definitions, core concepts, and exam-relevant facts. "
            "The summary must be dense and suitable for generating study materials."
        )
        
        # Use a faster model if possible
        summary = CourseContextEngine.ask_course_ai_raw(text, prompt)
        return summary

    @staticmethod
    def limit_total_ocr_text(text, max_chars=1500):
        """
        Extracts and limits total OCR text from consolidated notes.
        """
        # Find all [Contained in Notebook Image] or [Image OCR Content] blocks
        image_pattern = r"\[Contained in Notebook Image\]: (.*?)\n|\[Image OCR Content\]: (.*?)\n"
        matches = re.findall(image_pattern, text)
        
        all_ocr = []
        for match in matches:
            content = match[0] if match[0] else match[1]
            all_ocr.append(content)
        
        combined_ocr = " ".join(all_ocr)
        if len(combined_ocr) > max_chars:
            combined_ocr = combined_ocr[:max_chars] + "... [OCR Truncated]"
        
        # Remove all image blocks from original text and re-inject limited total
        cleaned_text = re.sub(image_pattern, "", text)
        if combined_ocr:
            cleaned_text += f"\n\n[Consolidated Image OCR Context]:\n{combined_ocr}"
            
        return cleaned_text

    @classmethod
    def ensure_quiz_chunks(cls, course_id):
        """
        Ensures that the course text is split into chunks for incremental quiz generation.
        """
        
        # 1. Check if chunks already exist
        if QuizChunk.objects.filter(course_id=course_id).exists():
            return True
            
        # 2. Get consolidated text
        notes_obj = CourseNotes.objects.filter(course_id=course_id).first()
        
        # Requirement #1: Ensure Document Text is Always Sent
        if not notes_obj or not notes_obj.extracted_text or len(notes_obj.extracted_text.strip()) < 100:
            logger.info(f"AI Optimizer: Triggering deep consolidation for Course {course_id}")
            CourseContextEngine.consolidate_course_notes(course_id)
            notes_obj = CourseNotes.objects.filter(course_id=course_id).first()
            
        if not notes_obj or not notes_obj.extracted_text or len(notes_obj.extracted_text.strip()) < 100:
            logger.error(f"AI Optimizer: No usable text found for Course {course_id}")
            return False
            
        # 3. Split into 3000-character chunks
        text = notes_obj.extracted_text
        chunk_size = 3000
        new_chunks = []
        
        # Simple character-based splitting to avoid scans
        for i in range(0, len(text), chunk_size):
            content = text[i:i + chunk_size]
            if len(content.strip()) < 200: continue # Skip fragments
            
            new_chunks.append(
                QuizChunk(
                    course_id=course_id,
                    content=content,
                    order=i // chunk_size
                )
            )
            
        if new_chunks:
            QuizChunk.objects.bulk_create(new_chunks)
            return True
        return False

    @classmethod
    def get_next_quiz_chunk(cls, course_id):
        """
        Retrieves a RANDOM unused chunk for the course to ensure syllabus coverage.
        """
        
        # Ensure chunks exist
        cls.ensure_quiz_chunks(course_id)
        
        # Get the next sequential unused chunk
        chunk = QuizChunk.objects.filter(course_id=course_id, is_used=False).order_by('order').first()
        
        if not chunk:
            # Requirement #3: Reset Logic
            # Mark all as unused and pick the first one
            QuizChunk.objects.filter(course_id=course_id).update(is_used=False)
            chunk = QuizChunk.objects.filter(course_id=course_id).order_by('order').first()
            
        if chunk:
            # We don't mark as used here; we wait for success
            return chunk.content
            
        return ""

    @classmethod
    def mark_chunk_used(cls, course_id, content):
        """
        Marks a specific chunk as used based on its content.
        Only called after successful generation.
        """
        QuizChunk.objects.filter(course_id=course_id, content=content).update(is_used=True)

    @classmethod
    def ensure_flashcard_chunks(cls, course_id):
        """
        Ensures that the course text is split into chunks for incremental flashcard generation.
        Chunk size: 2000 characters (per user request 1500-2500)
        """
        if FlashcardChunk.objects.filter(course_id=course_id).exists():
            return True
            
        notes_obj = CourseNotes.objects.filter(course_id=course_id).first()
        if not notes_obj or not notes_obj.extracted_text or len(notes_obj.extracted_text.strip()) < 100:
            CourseContextEngine.consolidate_course_notes(course_id)
            notes_obj = CourseNotes.objects.filter(course_id=course_id).first()
            
        if not notes_obj or not notes_obj.extracted_text:
            return False
            
        text = notes_obj.extracted_text
        chunk_size = 2000
        new_chunks = []
        
        for i in range(0, len(text), chunk_size):
            content = text[i:i + chunk_size]
            if len(content.strip()) < 150: continue
            
            new_chunks.append(
                FlashcardChunk(
                    course_id=course_id,
                    content=content,
                    order=i // chunk_size
                )
            )
            
        if new_chunks:
            FlashcardChunk.objects.bulk_create(new_chunks)
            return True
        return False

    @classmethod
    def get_next_flashcard_chunk(cls, course_id):
        """
        Retrieves the next chunk based on Course.flashcard_chunk_index
        """
        from course.models import Course
        cls.ensure_flashcard_chunks(course_id)
        
        course = Course.objects.filter(id=course_id).first()
        if not course: return ""
        
        idx = course.flashcard_chunk_index
        chunk = FlashcardChunk.objects.filter(course_id=course_id, order=idx).first()
        
        if not chunk:
            # Wrap around
            course.flashcard_chunk_index = 0
            course.save(update_fields=['flashcard_chunk_index'])
            chunk = FlashcardChunk.objects.filter(course_id=course_id, order=0).first()
            
        return chunk.content if chunk else ""

    @classmethod
    def increment_flashcard_index(cls, course_id):
        from course.models import Course
        Course.objects.filter(id=course_id).update(flashcard_chunk_index=models.F('flashcard_chunk_index') + 1)

    @classmethod
    def prepare_context(cls, course_id):
        """
        Orchestrates gathering and limiting context for a course.
        (Kept for backward compatibility or other AI features)
        """
        try:
            from course.models import CourseNotes
            notes_obj = CourseNotes.objects.filter(course_id=course_id).first()
            
            if not notes_obj:
                # Trigger consolidation if not present
                CourseContextEngine.consolidate_course_notes(course_id)
                notes_obj = CourseNotes.objects.filter(course_id=course_id).first()
            
            raw_text = notes_obj.extracted_text if notes_obj else ""
            if not raw_text:
                return ""

            # 1. Limit total OCR text
            text_with_limited_ocr = cls.limit_total_ocr_text(raw_text)
            
            # 2. Limit overall word count
            final_context = cls.limit_text_size(text_with_limited_ocr)
            
            return final_context
            
        except Exception as e:
            logger.error(f"AI Optimizer Error for Course {course_id}: {e}")
            return ""
