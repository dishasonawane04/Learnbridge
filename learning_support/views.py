from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from .services.support_engine import get_support_response
from .models import SupportSession, SupportMessage
import json
import json
import uuid
from analytics.models import ActivityLog
from course.models import CourseUnit

def support_home(request):
    """Renders the Learning Support Chat Interface with History."""
    # Get User or Session Key
    if request.user.is_authenticated:
        filter_kwargs = {'user': request.user}
    else:
        if not request.session.session_key:
            request.session.create()
        filter_kwargs = {'session_key': request.session.session_key}

    # Fetch all sessions
    all_sessions = SupportSession.objects.filter(**filter_kwargs)
    
    # Get Current Session
    chat_id = request.GET.get('chat_id')
    current_chat = None
    messages = []
    
    if chat_id:
        try:
            current_chat = SupportSession.objects.get(id=chat_id, **filter_kwargs)
            messages = current_chat.messages.all().order_by('created_at')
        except SupportSession.DoesNotExist:
            return redirect('support_home')
    
    # If no chat selected, don't auto-create one until they interact? 
    # Or maybe create one in memory? Let's just pass None and handle in template (Welcome Screen).
    # But if they start typing, we need a chat_id.
    
    return render(request, "learning_support/support_chat.html", {
        "all_sessions": all_sessions,
        "current_chat": current_chat,
        "chat_messages": messages
    })

def new_support_chat(request):
    """Creates a new support session and redirects to it."""
    if request.user.is_authenticated:
        user = request.user
        session_key = None
    else:
        if not request.session.session_key:
            request.session.create()
        user = None
        session_key = request.session.session_key

    new_chat = SupportSession.objects.create(
        user=user, 
        session_key=session_key,
        title="New Support Session"
    )
    return redirect(f"/support/?chat_id={new_chat.id}")

@csrf_exempt
def support_chat_api(request):
    """
    API for Support Chat.
    Handles Voice/Text, Persists Messages, and returns Streaming responses.
    """
    if request.method == "POST":
        try:
            # Parse Data
            if request.content_type.startswith('multipart'):
                data = request.POST
                user_message = data.get("message", "")
                mode = 'voice' if data.get("type") == 'voice' else 'text'
                chat_id = data.get("chat_id")
            else:
                data = json.loads(request.body)
                user_message = data.get("message", "")
                mode = 'text'
                chat_id = data.get("chat_id")

            # Get or Create Session
            session = None
            if chat_id:
                try:
                    session = SupportSession.objects.get(id=chat_id)
                except SupportSession.DoesNotExist:
                    pass
            
            if not session:
                # Determine user/key
                if request.user.is_authenticated:
                    u, k = request.user, None
                else:
                    if not request.session.session_key: request.session.create()
                    u, k = None, request.session.session_key
                
                session = SupportSession.objects.create(user=u, session_key=k, title=user_message[:30] + "...")
                new_chat_created = True
            else:
                new_chat_created = False
                # Update title if it's the first real message and title is default
                if session.title == "New Support Session":
                    session.title = user_message[:30] + "..."
                    session.save()

            # Save User Message
            SupportMessage.objects.create(session=session, sender='user', content=user_message)

            # --- ANALYTICS LOGGING ---
            if request.user.is_authenticated:
                ActivityLog.objects.create(
                    user=request.user,
                    app_name='learning_support',
                    activity_type='help_requested',
                    topic=session.title,
                    metadata={'session_id': str(session.id)}
                )
            # -------------------------

            # Define Streaming Generator Wrapper to Save AI Response
            def event_stream():
                full_response = []
                # First chunk: Send chat_id if new
                if new_chat_created:
                    yield json.dumps({"type": "meta", "chat_id": str(session.id)}) + "\n"

                # Prepare Context using Hybrid RAG
                from ai_core.ai_engine import get_hybrid_response_context
                
                course_id = request.session.get("active_course_id")
                if not course_id and session.course:
                    course_id = session.course.id
                elif not course_id and session.unit:
                    course_id = session.unit.course.id
                
                context_text, system_prompt, is_course_aware = get_hybrid_response_context(user_message, course_id)

                generator = get_support_response(
                    user_message, 
                    mode=mode, 
                    stream=True,
                    context=context_text,
                    custom_system_prompt=system_prompt
                )
                
                for chunk in generator:
                    full_response.append(chunk)
                    yield chunk
                
                # Save AI Message at end
                ai_text = "".join(full_response)
                SupportMessage.objects.create(session=session, sender='ai', content=ai_text)

            return StreamingHttpResponse(event_stream(), content_type='text/plain')

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid method"}, status=405)

def start_unit_support(request, unit_id):
    """Creates a new support session linked to a Course Unit."""
    unit = get_object_or_404(CourseUnit, id=unit_id)
    
    # Create Session linked to Unit
    if request.user.is_authenticated:
        session = SupportSession.objects.create(
            user=request.user,
            unit=unit,
            title=f"Help: {unit.title}"
        )
    else:
        # Require login for course features generally, but handle anonymous safe
        return redirect('course:list') # Or login

    return redirect(f'/support/?chat_id={session.id}')

def start_course_support(request, course_id):
    """Creates a new support session linked to a Course."""
    from course.models import Course
    course = get_object_or_404(Course, id=course_id)
    
    if request.user.is_authenticated:
        session = SupportSession.objects.create(
            user=request.user,
            course=course,
            title=f"Help: {course.title}"
        )
    else:
        return redirect('course:list')

    return redirect(f'/support/?chat_id={session.id}')
