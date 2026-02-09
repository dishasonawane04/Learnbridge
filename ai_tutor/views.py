from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import json
import os
from .models import Chat, ChatMessage
from .ai_logic import chat_with_ai
from analytics.models import ActivityLog
from course.models import CourseUnit

# @login_required # Removed for Anonymous Access
def tutor_home(request):
    """Renders the main AI Tutor interface with DB-backed history."""
    
    # Ensure session key exists
    if not request.session.session_key:
        request.session.create()
    
    # Filter by User OR Session Key
    if request.user.is_authenticated:
        chats = Chat.objects.filter(user=request.user, is_archived=False)
    else:
        chats = Chat.objects.filter(session_key=request.session.session_key, is_archived=False)
    
    context = {
        "all_chats": chats,
        "chat_history": [] 
    }
    return render(request, "ai_tutor/tutor.html", context)

@csrf_exempt
@csrf_exempt
# @login_required
def chat_api(request):
    """API Endpoint to handle chat messages and file uploads with Streaming Response."""
    if request.method == "POST":
        try:
            # Data Extraction
            if request.content_type.startswith('multipart'):
                data = request.POST
                user_message = data.get("message", "")
                msg_type = data.get("type", "text")
                chat_id = data.get("chat_id")
                uploaded_file = request.FILES.get('file')
            else:
                data = json.loads(request.body)
                user_message = data.get("message", "")
                msg_type = data.get("type", "text")
                chat_id = data.get("chat_id")
                uploaded_file = None

            # Get or Create Chat
            if chat_id:
                # Allow access if User matches OR Session Key matches
                if request.user.is_authenticated:
                    chat = get_object_or_404(Chat, id=chat_id, user=request.user)
                else:
                    if not request.session.session_key: request.session.create()
                    chat = get_object_or_404(Chat, id=chat_id, session_key=request.session.session_key)
            else:
                # Auto-title based on first message
                title = user_message[:30] + "..." if user_message else "New Chat"
                
                if request.user.is_authenticated:
                    chat = Chat.objects.create(user=request.user, title=title)
                else:
                    if not request.session.session_key: request.session.create()
                    chat = Chat.objects.create(session_key=request.session.session_key, title=title)

            # Path Handling for AI
            image_path = None
            doc_path = None
            file_url = None
            
            # Save User Message
            user_msg_obj = ChatMessage.objects.create(
                chat=chat,
                sender='user',
                content=user_message,
                msg_type=msg_type
            )

            # --- ANALYTICS LOGGING ---
            if request.user.is_authenticated and user_message:
                ActivityLog.objects.create(
                    user=request.user,
                    app_name='ai_tutor',
                    activity_type='question_asked',
                    topic=chat.title,
                    metadata={'chat_id': str(chat.id)}
                )
            # -------------------------

            if uploaded_file:
                # Save attachment
                user_msg_obj.attachment = uploaded_file
                user_msg_obj.save()
                
                # Get file path for AI
                full_path = user_msg_obj.attachment.path
                
                if msg_type == 'image':
                    image_path = full_path
                elif msg_type == 'doc':
                    doc_path = full_path

            # Update Chat timestamp
            chat.save() # Updates updated_at

            # If no message but file exists, set default prompt for AI (but don't change saved user content)
            prompt_for_ai = user_message
            if not user_message and (image_path or doc_path):
                prompt_for_ai = "Analyze this content."
            
            # --- STRICT CONTEXT INJECTION FROM MANDATORY CONTRACT ---
            from course.services.ai_context import get_system_prompt
            from core.ai.services import CourseContextEngine
            
            system_instruction = ""
            
            if chat.unit:
                # Use unitary context (legacy + specific unit focus)
                system_instruction = get_system_prompt(chat.unit.course, chat.unit)
            elif chat.course:
                # Use FULL COURSE context
                context_text = CourseContextEngine.get_course_context(chat.course.id)
                system_instruction = (
                    "You are a helpful teaching assistant for this specific course. "
                    "Use ONLY the following course notes to answer the student's question. "
                    "If the answer is not in the notes, say 'I cannot find this in the course material.'\n\n"
                    f"--- COURSE NOTES ---\n{context_text}\n--------------------\n"
                )
            else:
                # Fallback
                system_instruction = "SYSTEM: You are an academic AI assistant. Please ask the user to select a course."

            # Prepend system instruction to the prompt context for the AI service
            # (Assuming chat_with_ai supports system prompt or we prepend it)
            prompt_for_ai = f"{system_instruction}\n\nUSER QUESTION: {prompt_for_ai}"
            # -------------------------------------------------------

            mode = 'voice' if msg_type == 'voice' else 'text'

            # --- UNIVERSAL STREAMING RESPONSE ---
            def event_stream():
                ai_generator = chat_with_ai(
                    prompt=prompt_for_ai,
                    image_path=image_path,
                    document_path=doc_path,
                    mode=mode,
                    stream=True
                )
                
                full_response = ""
                for chunk in ai_generator:
                    full_response += chunk
                    yield chunk

                # --- POST-STREAM: SAVE AI MESSAGE ---
                # This executes after the last chunk is yielded (and hopefully sent)
                ChatMessage.objects.create(
                    chat=chat,
                    sender='ai',
                    content=full_response,
                    msg_type='text'
                )
                
                # Signal Chat ID if it was new (Client might need it)
                # Ideally, client should have got ID from a separate 'create' call or we send it in headers?
                # With text stream, we can't easily send JSON metadata.
                # Solution: Client reloads or handles 'currentChatId' logic.
                pass

            response = StreamingHttpResponse(event_stream(), content_type='text/plain')
            # If new chat, send ID in header so client can update URL/State
            response['X-Chat-ID'] = str(chat.id)
            return response

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
@csrf_exempt
# @login_required
def new_chat(request):
    """Creates a fresh chat."""
    if request.method == "POST":
        if request.user.is_authenticated:
            chat = Chat.objects.create(user=request.user, title="New Chat")
        else:
            if not request.session.session_key: request.session.create()
            chat = Chat.objects.create(session_key=request.session.session_key, title="New Chat")
            
        return JsonResponse({"status": "success", "chat_id": str(chat.id)})
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
# @login_required
def load_chat_history(request, chat_id):
    """Loads messages for a specific chat."""
    if request.user.is_authenticated:
        chat = get_object_or_404(Chat, id=chat_id, user=request.user)
    else:
        if not request.session.session_key: request.session.create()
        chat = get_object_or_404(Chat, id=chat_id, session_key=request.session.session_key)
    messages = chat.messages.all().order_by('created_at')
    
    history = []
    for msg in messages:
        history.append({
            "sender": msg.sender,
            "text": msg.content,
            "type": msg.msg_type,
            "file_url": msg.attachment.url if msg.attachment else None
        })
    
    return JsonResponse({"status": "success", "chat_id": str(chat.id), "title": chat.title, "messages": history})

# --- MANAGEMENT ACTIONS ---

@csrf_exempt
@login_required
def rename_chat(request, chat_id):
    if request.method == "POST":
        data = json.loads(request.body)
        new_title = data.get("title")
        if request.user.is_authenticated:
            chat = get_object_or_404(Chat, id=chat_id, user=request.user)
        else:
            chat = get_object_or_404(Chat, id=chat_id, session_key=request.session.session_key)
        chat.title = new_title
        chat.save()
        return JsonResponse({"status": "success"})
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
@csrf_exempt
# @login_required
def delete_chat(request, chat_id):
    if request.method == "POST":
        if request.user.is_authenticated:
            chat = get_object_or_404(Chat, id=chat_id, user=request.user)
        else:
            chat = get_object_or_404(Chat, id=chat_id, session_key=request.session.session_key)
        chat.delete()
        return JsonResponse({"status": "success"})
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
@csrf_exempt
# @login_required
def archive_chat(request, chat_id):
    if request.method == "POST":
        if request.user.is_authenticated:
            chat = get_object_or_404(Chat, id=chat_id, user=request.user)
        else:
            chat = get_object_or_404(Chat, id=chat_id, session_key=request.session.session_key)
        chat.is_archived = not chat.is_archived # Toggle
        chat.save()
        return JsonResponse({"status": "success", "is_archived": chat.is_archived})
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
@csrf_exempt
# @login_required
def pin_chat(request, chat_id):
    if request.method == "POST":
        if request.user.is_authenticated:
            chat = get_object_or_404(Chat, id=chat_id, user=request.user)
        else:
            chat = get_object_or_404(Chat, id=chat_id, session_key=request.session.session_key)
        chat.is_pinned = not chat.is_pinned # Toggle
        chat.save()
        return JsonResponse({"status": "success", "is_pinned": chat.is_pinned})
    return JsonResponse({"error": "Invalid method"}, status=405)

# @login_required
def archived_chats(request):
    """Renders the list of archived chats."""
    # Ensure session key
    if not request.session.session_key: request.session.create()
    
    if request.user.is_authenticated:
        chats = Chat.objects.filter(user=request.user, is_archived=True)
    else:
        chats = Chat.objects.filter(session_key=request.session.session_key, is_archived=True)
        
    return render(request, "ai_tutor/archived.html", {"chats": chats})

def shared_chat(request, token):
    """Public read-only view of a shared chat."""
    chat = get_object_or_404(Chat, share_token=token)
    messages = chat.messages.all().order_by('created_at')
    return render(request, "ai_tutor/shared_chat.html", {"chat": chat, "messages": messages})

@csrf_exempt
# @login_required
def get_share_link(request, chat_id):
    """Returns the share link for a chat."""
    if request.user.is_authenticated:
        chat = get_object_or_404(Chat, id=chat_id, user=request.user)
    else:
        chat = get_object_or_404(Chat, id=chat_id, session_key=request.session.session_key)
    # Ensure absolute URL
    share_url = request.build_absolute_uri(f"/ai/share/{chat.share_token}/")
    return JsonResponse({"status": "success", "url": share_url})

@login_required
def start_unit_chat(request, unit_id):
    """Start a new chat session for a specific unit"""
    unit = get_object_or_404(CourseUnit, id=unit_id)
    
    # Check if user already has a chat for this unit
    existing_chat = Chat.objects.filter(user=request.user, unit=unit).first()
    
    if existing_chat:
        # Redirect to existing chat
        return render(request, "ai_tutor/tutor.html", {
            "all_chats": Chat.objects.filter(user=request.user, is_archived=False),
            "active_chat": existing_chat,
            "chat_history": existing_chat.messages.all(),
            "unit": unit
        })
    
    # Create new chat for this unit
    chat = Chat(
        user=request.user,
        unit=unit,
        course=unit.course,
        title=f"Study: {unit.title}"
    )
    chat.save()
    
    return render(request, "ai_tutor/tutor.html", {
        "all_chats": Chat.objects.filter(user=request.user, is_archived=False),
        "active_chat": chat,
        "chat_history": [],
        "unit": unit
    })

@login_required
def start_course_chat(request, course_id):
    """Start a new global chat session for a specific course"""
    from course.models import Course
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user has access (owner or logged in? Student enrolled?)
    # For now, if they can view the course, they can chat.
    # We should probably check enrollment if we had it, but here we assume open access or check course user?
    # Spec says: "Tutor must now work course-wise."
    
    # Create new chat for this course
    chat = Chat(
        user=request.user,
        course=course,
        title=f"Course Help: {course.title}"
    )
    chat.save()
    
    return render(request, "ai_tutor/tutor.html", {
        "all_chats": Chat.objects.filter(user=request.user, is_archived=False),
        "active_chat": chat,
        "chat_history": [],
        "course": course
    })
