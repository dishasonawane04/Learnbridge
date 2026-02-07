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

        # --- STRICT CONTEXT INJECTION ---
        from course.models import Course, CourseUnit
        from course.services.ai_context import get_system_prompt
        
        course_id = request.GET.get('course_id') or request.POST.get('course_id')
        unit_id = request.GET.get('unit_id') or request.POST.get('unit_id')
        
        system_prompt = "SYSTEM:\nYou are an academic AI assistant."
        
        if unit_id:
             unit = get_object_or_404(CourseUnit, id=unit_id)
             system_prompt = get_system_prompt(unit.course, unit)
        elif course_id:
             course = get_object_or_404(Course, id=course_id)
             # Fallback if only course provided (though strictly should represent unit)
             system_prompt = f"SYSTEM:\nYou are an academic AI assistant for the course {course.title}."

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
        "topic": topic
    })

def generate_unit_notes(request, unit_id):
    """Initializes note generation from a Course Unit."""
    from course.models import CourseUnit
    from django.shortcuts import get_object_or_404
    unit = get_object_or_404(CourseUnit, id=unit_id)
    return redirect(f"{reverse('notes:notes')}?unit_id={unit.id}&topic={unit.title}")
