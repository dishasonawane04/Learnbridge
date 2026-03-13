from ai_engine.concept_map_generator import generate_concept_map_data
from course.models import ConceptMap, Course
from notes.models import Note

class ConceptMapService:
    @staticmethod
    def generate_for_course(course_id, user):
        """Generates or updates a concept map for the entire course based on all notes."""
        course = Course.objects.get(id=course_id)
        
        # Consolidate all available text sources for this course
        # 1. Note objects
        notes_text = "\n\n".join([n.content for n in Note.objects.filter(course=course, user=user) if n.content])
        
        # 2. CourseMaterial objects (extracted text from uploaded files)
        materials_text = "\n\n".join([m.extracted_text for m in course.course_materials.all() if m.extracted_text])
        
        # 3. CourseUnit objects (lesson content)
        units_text = "\n\n".join([u.content for u in course.units.all() if u.content])
        
        # 4. Primary Course object (extracted text from initial upload)
        course_text = course.extracted_text if course.extracted_text else ""
        
        consolidated_text = "\n\n".join([notes_text, materials_text, units_text, course_text]).strip()
        
        if not consolidated_text:
            return None, "No notes available to generate concept map."
            
        map_data = generate_concept_map_data(consolidated_text)
        if not map_data:
            return None, "AI Concept Map generation timed out or failed. Please check if Ollama is running and try again."
            
        concept_map, created = ConceptMap.objects.update_or_create(
            course=course,
            user=user,
            defaults={'data': map_data}
        )
        return concept_map, None

    @staticmethod
    def generate_for_note(note_id):
        """Triggered when a single note is saved."""
        note = Note.objects.get(id=note_id)
        if not note.course:
            return None
            
        # For now, we update the whole course map whenever a note is saved
        map_obj, error_msg = ConceptMapService.generate_for_course(note.course.id, note.user)
        return map_obj
