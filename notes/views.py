from django.shortcuts import render, redirect, get_object_or_404
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

        from course.services.ai_context import get_course_context
        course_id = request.GET.get('course_id')
        context = ""
        if course_id:
            context = get_course_context(course_id=course_id)
            context = f"\nUse the following CONTEXT for these notes:\n{context}\n"

        client = ollama.AsyncClient()

        try:
            res = await client.chat(
                model=settings.OLLAMA_MODEL_TEXT,
                messages=[{
                    'role': 'user',
                    'content': f"Generate comprehensive, exam-oriented notes for the topic: '{topic}'. {context}{structure_hint}"
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
    
    return await sync_to_async(render)(request, "notes/generate.html", {
        "response": response,
        "topic": topic
    })
