import re
import logging
from django.conf import settings
from core.ai.services import CourseContextEngine

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
    def prepare_context(cls, course_id):
        """
        Orchestrates gathering and limiting context for a course.
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
