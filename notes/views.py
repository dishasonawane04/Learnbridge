from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import Note
from core.utils import log_activity
from asgiref.sync import sync_to_async
import ollama
import markdown

@login_required
def notes_list(request):
    notes = Note.objects.filter(user=request.user)
    return render(request, 'notes/list.html', {'notes': notes})

@login_required
def note_detail(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    # Convert markdown to HTML for display
    html_content = markdown.markdown(note.content)
    return render(request, 'notes/detail.html', {'note': note, 'html_content': html_content})

async def generate_notes(request):
    response = None
    topic = request.GET.get('topic', '')
    
    # Structure requirement for the prompt
    structure_hint = """
    FORMAT:
    # [Topic Name]
    ## Definition
    ## Key Concepts
    ## Important Formulas (if any)
    ## Example
    ## Exam Tips
    """

    if request.method == "POST":
        topic = request.POST.get("topic", topic)
        action = request.POST.get("action", "generate")

        if action == "save":
            content = request.POST.get("content")
            if content:
                await sync_to_async(Note.objects.create)(
                    user=request.user,
                    topic=topic,
                    content=content
                )
                return redirect('notes_list')

        # --- CENTRALIZED CONTEXT INJECTION ---
        from core.ai.services import CourseContextEngine
        
        course_id = request.session.get("active_course_id") or request.GET.get('course_id') or request.POST.get('course_id')
        
        context_text = CourseContextEngine.get_course_context(course_id)
        
        system_prompt = (
            "You are an academic AI assistant. "
            "Use ONLY the following study material to generate notes. "
            "If the information is not in the material, say you cannot find it."
            f"\n--- COURSE NOTES ---\n{context_text}\n---------------------\n"
        )

        final_prompt = f"""{system_prompt}
        
        TASK:
        Generate comprehensive, exam-oriented notes for the topic: '{topic}'.
        {structure_hint}
        """

        client = ollama.AsyncClient()

        try:
            res = await client.chat(
                model=settings.OLLAMA_MODEL_TEXT,
                messages=[{
                    'role': 'user',
                    'content': final_prompt
                }]
            )
            response = res['message']['content']
        except Exception as e:
            response = f"Error generating notes: {str(e)}"

        # Log Activity
        await sync_to_async(log_activity)(
            user=request.user,
            app_name="notes",
            topic=topic,
            input_type="text",
            time_spent=60,
            outcome="completed"
        )
    
    # Render response as HTML if it exists
    response_html = ""
    if response and not response.startswith("Error"):
        response_html = markdown.markdown(response, extensions=['fenced_code', 'tables'])
    else:
        response_html = response

    return await sync_to_async(render)(request, "notes/generate.html", {
        "response": response,
        "response_html": response_html,
        "topic": topic,
        "course_id": course_id
    })

def generate_unit_notes(request, unit_id):
    """Initializes note generation from a Course Unit."""
    from course.models import CourseUnit
    from django.shortcuts import get_object_or_404
    from urllib.parse import urlencode
    
    unit = get_object_or_404(CourseUnit, id=unit_id)
    base_url = reverse('notes:notes')
    query_string = urlencode({'unit_id': unit.id, 'topic': unit.title})
    return redirect(f"{base_url}?{query_string}")
