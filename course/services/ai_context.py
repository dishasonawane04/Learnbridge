from ..models import Course, CourseUnit, CourseMaterial
import random

def get_course_context(course_id=None, unit_id=None):
    """
    Returns a consolidated text blob of the course/unit content.
    Used as context for AI features (Quiz, Notes, etc.)
    """
    context = ""
    
    if unit_id:
        materials = CourseMaterial.objects.filter(unit_id=unit_id)
        unit = CourseUnit.objects.get(id=unit_id)
        context += f"UNIT: {unit.title}\n"
        for mat in materials:
            context += f"--- CONTENT FROM {mat.file.name} ---\n"
            context += mat.extracted_text + "\n"
            
    elif course_id:
        course = Course.objects.get(id=course_id)
        context += f"COURSE: {course.title}\nDESCRIPTION: {course.description}\n"
        units = course.units.all()
        for unit in units:
            context += f"\nUNIT: {unit.title}\n"
            for mat in unit.materials.all():
                context += mat.extracted_text + "\n"
                
    return context

def get_system_prompt(course, unit):
    """
    Generates the strict system prompt for the AI assistant.
    Adheres to the MANDATORY contract.
    """
    # Build unit context
    unit_overview = unit.overview if unit.overview else "No learning objectives provided."
    unit_content = unit.content if unit.content else ""
    
    return f"""SYSTEM:
You are an academic AI assistant inside Learnbridge.

CONTEXT:
Course Title: {course.title}
Course Level: {course.get_level_display()}
Unit Title: {unit.title}
Unit Overview/Syllabus: {unit_overview}
{f"Unit Content: {unit_content[:500]}..." if unit_content else ""}

RULES:
- Stay strictly within the unit syllabus and learning objectives
- No hallucination or external information
- Match the {course.get_level_display()} level
- Provide structured, academic output
- If content is insufficient, acknowledge limitations

TASK:
"""

def query_ai_service(user_message, system_prompt):
    """
    Mock AI service for development. 
    In production, this would call an LLM API (e.g., OpenAI, Ollama).
    """
    # Simulate processing time or logic
    return f"**Academic Response:**\n\nThank you for your question regarding '{user_message}'. Based on the syllabus for **{system_prompt.split('Unit Title: ')[1].splitlines()[0]}**, I can provide the following explanation...\n\n(This is a placeholder response verifying the system prompt injection is working.)"
