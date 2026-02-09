import json
import logging
from typing import List, Dict, Any
from course.models import CourseUnit, ConceptNode, KnowledgeRelationship

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

import requests
from django.conf import settings

class CourseContextEngine:
    """
    Central engine for retrieving course context and querying AI.
    """
    
    @staticmethod
    def get_course_context(course_id: int) -> str:
        """
        Retrieves all text content from a course (units + materials).
        """
        try:
            from course.models import Course
            course = Course.objects.get(id=course_id)
            units = course.units.all().prefetch_related('materials')
            
            context_parts = []
            context_parts.append(f"COURSE TITLE: {course.title}")
            context_parts.append(f"DESCRIPTION: {course.description}\n")
            
            for unit in units:
                context_parts.append(f"--- LESSON: {unit.title} ---")
                if unit.content:
                    context_parts.append(unit.content)
                
                # If there's an uploaded file on the unit (our new field)
                # We assume content extraction happened or we just note it.
                # Ideally, content extraction updates unit.content.
                
                # Check legacy materials
                for mat in unit.materials.all():
                    if mat.extracted_text:
                        context_parts.append(f"[Material: {mat.file_type}]")
                        context_parts.append(mat.extracted_text)
                        
                context_parts.append("\n")
                
            return "\n".join(context_parts)
        except Exception as e:
            logger.error(f"Error getting course context: {e}")
            return ""

    @staticmethod
    def ask_course_ai(course_id: int, question: str) -> str:
        """
        Asks the AI a question based strictly on the course context.
        """
        context = CourseContextEngine.get_course_context(course_id)
        
        if not context.strip():
            return "I cannot find any content in this course to answer your question."
            
        system_prompt = (
            "You are a helpful teaching assistant for this specific course. "
            "Use ONLY the following course notes to answer the student's question. "
            "If the answer is not in the notes, say 'I cannot find this in the course material.' "
            "Do not halluncinate or use outside knowledge.\n\n"
            f"--- COURSE NOTES ---\n{context}\n--------------------\n"
        )
        
        return CourseContextEngine._query_ollama(system_prompt, question)

    @staticmethod
    def _query_ollama(system: str, user_msg: str) -> str:
        try:
            model = "llama3" # Enforce llama3
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": f"{system}\n\nStudent: {user_msg}\nAI:",
                    "stream": False,
                    "options": {
                        "temperature": 0.3 # Low temperature for factual recall
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json().get('response', "Error: Empty response from AI.")
        except Exception as e:
            logger.error(f"Ollama Error: {e}")
            return f"Error contacting AI service: {e}"
