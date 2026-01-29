import os
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import ollama
from asgiref.sync import sync_to_async
from core.utils import log_activity

@sync_to_async
def get_chat_history(request):
    return request.session.get('chat_history', [])

@sync_to_async
def update_history(request, user_input, response, image_url=None):
    if 'chat_history' not in request.session:
        request.session['chat_history'] = []
    
    request.session['chat_history'].append({'role': 'user', 'content': user_input, 'image': image_url})
    request.session['chat_history'].append({'role': 'ai', 'content': response})
    request.session.modified = True

@sync_to_async
def clear_history(request):
    if 'chat_history' in request.session:
        del request.session['chat_history']

@sync_to_async
def get_user(request):
    return request.user

async def sentence_explain(request):
    # Clear history if requested
    if request.GET.get('clear'):
        await clear_history(request)
        return redirect('sentence_explain')

    # Ensure history exists (conceptually, though get_chat_history handles empty default)
    
    if request.method == "POST":
        sentence = request.POST.get("sentence")
        image = request.FILES.get("image")
        print(f"DEBUG: Input Sentence: {sentence}") # Debug log
        
        user_input = sentence
        if image:
            user_input = "[Uploaded Image]" 
        
        client = ollama.AsyncClient()

        image_url = None
        response = None

        from course.services.ai_context import get_course_context
        course_id = request.GET.get('course_id')
        context = ""
        if course_id:
            context = get_course_context(course_id=course_id)
            context = f"\nUse the following COURSE CONTEXT for domain accuracy:\n{context}\n"

        if image:
             def save_file(img):
                fs = FileSystemStorage()
                filename = fs.save(img.name, img)
                return fs.url(filename), fs.path(filename)
            
             image_url, image_path = await sync_to_async(save_file)(image)

             try:
                res = await client.chat(
                    model=settings.OLLAMA_MODEL_VISION,
                    messages=[{
                        'role': 'user',
                        'content': f"Explain the complex sentences from this image in simple, plain English. {context} Do not use markdown, asterisks, or special symbols. Just plain text suitable for reading aloud. If a sentence is provided here: '{sentence}', focus on that.",
                        'images': [image_path]
                    }]
                )
                response = res['message']['content']
             except Exception as e:
                response = f"Error processing image: {str(e)}"

        elif sentence:
            try:
                res = await client.chat(
                    model=settings.OLLAMA_MODEL_TEXT,
                    messages=[{
                        'role': 'user',
                        'content': f"Explain this sentence in simple, plain English interactions. {context} Do NOT use markdown, bolding (**), or bullet points. Use natural conversational paragraphs only. Sentence to explain: '{sentence}'. Also provide a real-world example in plain text."
                    }]
                )
                response = res['message']['content']
            except Exception as e:
                response = f"Error generating explanation: {str(e)}"

        # Update History via Async Wrapper
        await update_history(request, user_input, response, image_url)

        # Log Activity
        user = await get_user(request)
        await sync_to_async(log_activity)(
            user=user,
            app_name="sentence_explain",
            topic=sentence[:50] if sentence else "Textbook OCR",
            input_type="image" if image else "text",
            time_spent=40,
            outcome="completed"
        )

    # Get history for render
    history = await get_chat_history(request)
    last_response = history[-1]['content'] if history else None

    return await sync_to_async(render)(request, "sentence_explain/explain.html", {
        "chat_history": history,
        "last_response": last_response
    })
