import json
import logging
import requests
from typing import List, Dict, Any
from django.conf import settings
from course.models import Course, CourseUnit, CourseMaterial, ConceptNode, KnowledgeRelationship, CourseContext

logger = logging.getLogger(__name__)

class ContentIntelligenceEngine:
    """
    Principal engine for decomposing course materials into atomic concept nodes
    and mapping semantic relationships.
    """

    @staticmethod
    def parse_unit_into_concepts(unit: CourseUnit, content_text: str = None) -> List[ConceptNode]:
        """
        Uses AI to extract concept nodes from unit content or materials.
        """
        text_to_analyze = content_text or unit.content or unit.overview
        if not text_to_analyze:
            logger.warning(f"No content found for unit {unit.id} to parse.")
            return []

        # In a production environment, this would call an LLM (GPT-4o/Claude)
        # using a structured JSON prompt matching the ConceptNode schema.
        
        # --- PROMPT LOGIC (Conceptual) ---
        # prompt = f"Decompose the following educational content into atomic concepts: {text_to_analyze}"
        # prompt += "Return JSON list: [{title, description, taxonomy_level, difficulty_index, order}]"
        
        # For Phase 1 Execution, we implement the internal processing logic
        # and provide a robust extraction interface.
        
        try:
            # Simulated AI Response for initial verification
            # In Phase 2, this will be replaced by a real deep_learning_extract() call
            extracted_data = ContentIntelligenceEngine._simulated_llm_extraction(text_to_analyze)
            
            concept_nodes = []
            for i, data in enumerate(extracted_data):
                concept, created = ConceptNode.objects.update_or_create(
                    unit=unit,
                    title=data['title'],
                    defaults={
                        'description': data.get('description', ''),
                        'taxonomy_level': data.get('taxonomy_level', 'understand'),
                        'difficulty_index': data.get('difficulty_index', 0.5),
                        'order': i
                    }
                )
                concept_nodes.append(concept)
            
            return concept_nodes

        except Exception as e:
            logger.error(f"Error in ContentIntelligenceEngine: {e}")
            return []

    @staticmethod
    def _simulated_llm_extraction(text: str) -> List[Dict[str, Any]]:
        """Mock LLM response for structural verification"""
        # Logic to return some nodes based on keywords if text is provided
        if "Machine Learning" in text or "ML" in text:
            return [
                {"title": "Introduction to Supervised Learning", "taxonomy_level": "remember", "difficulty_index": 0.3},
                {"title": "Linear Regression Mathematics", "taxonomy_level": "apply", "difficulty_index": 0.6},
                {"title": "Cost Functions and Optimization", "taxonomy_level": "analyze", "difficulty_index": 0.8}
            ]
        return [
            {"title": f"Core Concept 1", "taxonomy_level": "understand", "difficulty_index": 0.4},
            {"title": f"Application of {text[:20]}...", "taxonomy_level": "apply", "difficulty_index": 0.7}
        ]

    @staticmethod
    def create_knowledge_graph(unit: CourseUnit):
        """Processes dependencies between concepts within a unit"""
        concepts = unit.concepts.all().order_by('order')
        if concepts.count() < 2:
            return

        # Simple linear prerequisite mapping for Phase 1
        # Phase 2 will use LLM to detect non-linear dependencies
        for i in range(len(concepts) - 1):
            KnowledgeRelationship.objects.get_or_create(
                source=concepts[i],
                target=concepts[i+1],
                relation_type='prereq'
            )

class ProcessingPipeline:
    """Automated pipeline: Extraction → Chunking → Concept Mining → Embeddings"""

    @staticmethod
    def process_course_material(material: CourseMaterial):
        """Full pipeline for a newly uploaded material"""
        # 1. Extraction (Assumed already done by material.save() or trigger)
        text = material.extracted_text
        if not text:
            return

        # 2. Chunking
        chunks = ProcessingPipeline._chunk_text(text)
        
        # 3. Concept Mining
        concepts = ProcessingPipeline._mine_concepts(text)
        material.key_topics = concepts
        
        # 4. Update Summary
        material.summary = ProcessingPipeline._generate_summary(text[:2000])
        material.save()

        # 5. Sync to CourseContext
        ProcessingPipeline.sync_to_course_context(material.course)

    @staticmethod
    def sync_to_course_context(course: Course):
        """Aggregate all material data into the central CourseContext"""
        context_obj, _ = CourseContext.objects.get_or_create(course=course)
        
        all_materials = course.course_materials.all()
        aggregated_concepts = set()
        glossary = {}

        for mat in all_materials:
            if mat.key_topics:
                aggregated_concepts.update(mat.key_topics)
            
        context_obj.important_concepts = list(aggregated_concepts)
        # In a real app, glossary would be extracted via LLM
        context_obj.save()

    @staticmethod
    def _chunk_text(text: str, size: int = 1000) -> List[str]:
        """Simple character-based chunking with overlap"""
        return [text[i:i+size] for i in range(0, len(text), size - 100)]

    @staticmethod
    def _mine_concepts(text: str) -> List[str]:
        """Extract key topics using simple frequency or LLM"""
        # Placeholder: Return top keywords for now
        # In Phase 2, this will be an Ollama call
        words = text.split()
        if len(words) < 10: return []
        return list(set([w.strip(',.()').title() for w in words if len(w) > 5]))[:10]

    @staticmethod
    def _generate_summary(text: str) -> str:
        """Generate a brief summary of the text chunk"""
        system = "Summarize the following educational content in 2-3 sentences."
        return CourseContextEngine._query_ollama(system, text[:1500])

class CourseContextEngine:
    """
    Central engine for retrieving course context and querying AI.
    """
    
    @staticmethod
    def get_course_context(course_id: int) -> str:
        """
        Retrieves consolidated text content from CourseNotes.
        """
        try:
            from course.models import CourseNotes
            notes = CourseNotes.objects.filter(course_id=course_id).first()
            if notes:
                return notes.extracted_text
            
            # Fallback to dynamic consolidation if notes don't exist yet
            return CourseContextEngine.consolidate_course_notes(course_id)
        except Exception as e:
            logger.error(f"Error getting course context: {e}")
            return ""

    @staticmethod
    def consolidate_course_notes(course_id: int):
        """
        Gathers all extracted text from course materials, user notes, and images,
        and consolidates into the CourseNotes model for the course.
        """
        try:
            course = Course.objects.get(id=course_id)
            materials = course.course_materials.all().order_by('created_at')
            
            consolidated_text = []
            
            # 1. Base Materials
            for mat in materials:
                if mat.extracted_text:
                    consolidated_text.append(f"--- Document: {mat.file.name} ---")
                    consolidated_text.append(mat.extracted_text)
                    consolidated_text.append("\n")
            
            # 2. User Notes & Image OCR
            from notes.models import Note
            user_notes = Note.objects.filter(course=course).prefetch_related('images')
            if user_notes.exists():
                consolidated_text.append("--- USER ADDED NOTES & HANDWRITTEN CONTENT ---")
                for note in user_notes:
                    consolidated_text.append(f"Note Topic: {note.topic}")
                    consolidated_text.append(note.content)
                    
                    # Append OCR text from images
                    for img in note.images.all():
                        if img.extracted_text:
                            consolidated_text.append(f"[Contained in Notebook Image]: {img.extracted_text}")
                    consolidated_text.append("\n")

            from course.models import CourseNotes
            notes, _ = CourseNotes.objects.get_or_create(course=course)
            notes.extracted_text = "\n".join(consolidated_text)
            notes.save()
            
            # Step 2: Trigger RAG Chunking & Embedding
            from ai_core.services import process_course_notes_into_knowledge_store
            process_course_notes_into_knowledge_store(course_id, notes.extracted_text)
            
            return notes.extracted_text
        except Exception as e:
            logger.error(f"Error consolidating course notes: {e}")
            return ""

    @staticmethod
    def ask_course_ai(course_id: int, prompt: str, specialized_mode: str = None) -> str:
        """
        Queries AI about a specific course using Hybrid RAG.
        Optimized for SPEED with Fast Path and Model Neutralization.
        """
        from ai_core.ai_engine import get_hybrid_response_context, get_specialized_system_prompt
        from ai_engine.retriever import retrieve_diverse_context
        from course.models import CourseNotes
        
        # 1. Faster Context Retrieval
        context_text = ""
        if specialized_mode == 'summary':
            # Use CourseNotes directly for "Fast Path" if total text is reasonable
            notes = CourseNotes.objects.filter(course_id=course_id).first()
            if notes and len(notes.extracted_text) < 25000: # Increased threshold for speed
                logger.info(f"Summary: Fast Path triggered for Course {course_id}")
                context_text = notes.extracted_text[:20000] # Use more text directly
            else:
                logger.info(f"Summary: Using fast similarity retrieval.")
                from ai_engine.retriever import retrieve_context
                context_text = retrieve_context(prompt, course_id, k=8)
            
            system_prompt = get_specialized_system_prompt(mode='summary')
        else:
            context_text, system_prompt, is_course_aware = get_hybrid_response_context(prompt, course_id)
        
        # 2. Query Ollama with dynamic model and speed constraints
    @staticmethod
    def ask_course_ai_raw(user_msg: str, system_prompt: str = "You are a helpful assistant.") -> str:
        """
        Directly queries the AI without course-specific retrieval.
        Useful for summarization or simple transformations.
        """
        return CourseContextEngine._query_ollama(system_prompt, user_msg)

    @staticmethod
    def _query_ollama(system: str, user_msg: str, **kwargs) -> str:
        try:
            # Neutralize model choice for speed (OLLAMA_MODEL_TEXT is usually 1B)
            model = getattr(settings, 'OLLAMA_MODEL_TEXT', 'llama3.2:1b')
            
            options = {
                "temperature": 0.3,
                "num_predict": 400,
                "top_k": 30
            }
            options.update(kwargs)
            
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": f"{system}\n\nStudent: {user_msg}\nAI:",
                    "stream": False,
                    "options": options
                },
                timeout=300
            )
            response.raise_for_status()
            return response.json().get('response', "Error: Empty response from AI.")
        except Exception as e:
            logger.error(f"Ollama Error: {e}")
            return f"Error contacting AI service: {e}"
