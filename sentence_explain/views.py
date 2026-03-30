import os
from django.shortcuts import render, redirect
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from core.utils import log_activity

def sentence_explain(request):
    """
    Synchronous view that renders the explainer page and handles clear history.
    """
    if request.GET.get('clear'):
        if 'chat_history' in request.session:
            del request.session['chat_history']
        return redirect('sentence_explain:sentence_explain')

    history = request.session.get('chat_history', [])
    active_course_id = request.session.get("active_course_id")
    
    return render(request, "sentence_explain/explain.html", {
        "chat_history": history,
        "course_id": active_course_id
    })

@csrf_exempt
def sentence_explain_api(request):
    """
    API endpoint for the Sentence Explainer. Returns a streaming response.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    sentence = request.POST.get("sentence", "")
    language = request.POST.get("language", "English")
    image = request.FILES.get("image")
    course_id = request.session.get("active_course_id")

    user_input = sentence
    if image:
        user_input = "[Uploaded Image]"

    image_url = None
    image_path = None

    if image:
        from django.core.files.storage import FileSystemStorage
        fs = FileSystemStorage()
        filename = fs.save(image.name, image)
        image_url = fs.url(filename)
        image_path = fs.path(filename)

    # Construct the instruction
    context_text = ""
    if course_id:
        from ai_engine.retriever import retrieve_diverse_context
        context_text = retrieve_diverse_context(course_id, query=sentence, k=5)

    context_instruction = ""
    if context_text and context_text.strip():
        context_instruction = (
            f"\n### COURSE CONTEXT INFORMATION ###\n"
            f"The following excerpts are from the student's active course material. "
            f"PRIORITIZE this information. \n\n"
            f"--- CONTEXT START ---\n{context_text}\n--- CONTEXT END ---\n"
        )
    else:
        context_instruction = "\n(No specific course context found. Use general knowledge but add a disclaimer if outside course scope.)\n"

    prompt_style = (
        "You are a professional 'Sentence Explainer' for students. Break down complex concepts "
        "into clear, easy-to-understand language. \n\n"
        "RESPONSE STRUCTURE (Use these exact Markdown headers):\n"
        "### 📘 Explanation\n"
        "(Detailed explanation of the concept/sentence)\n\n"
        "### 💡 Key Points\n"
        "(Bullet points of the most important takeaways)\n\n"
        "### 📝 Example\n"
        "(A relatable, real-world scenario or application)\n\n"
        "GUIDELINES:\n"
        "1. Use clear, encouraging tone.\n"
        "2. Define difficult terms within the explanation.\n"
        "3. PRIORITIZE the provided COURSE CONTEXT. If not found, use general knowledge with: '[Note: This is general knowledge]'.\n"
        "4. Use Markdown for visual hierarchy (headers, bolding, lists).\n"
    )

    model = settings.OLLAMA_MODEL_TEXT
    if image:
        model = settings.OLLAMA_MODEL_VISION

    final_prompt = f"{prompt_style} {context_instruction} \n\n Task: Explain in '{language}': '{sentence or 'Image content'}'\n\nEnsure the response is strictly in {language}."

    # Streaming Response
    from ai_tutor.ai_logic import chat_with_ai
    
    try:
        # Check connection or start generator
        ai_generator = chat_with_ai(
            prompt=final_prompt,
            image_path=image_path,
            stream=True,
            course_id=course_id,
        )

        def event_stream():
            try:
                full_response = ""
                for chunk in ai_generator:
                    full_response += chunk
                    yield chunk

                # Post-processing: Update history
                if 'chat_history' not in request.session:
                    request.session['chat_history'] = []
                
                request.session['chat_history'].append({'role': 'user', 'content': user_input, 'image': image_url})
                request.session['chat_history'].append({'role': 'ai', 'content': full_response})
                request.session.modified = True
                request.session.save()

                # Log Activity
                log_activity(
                    user=request.user if request.user.is_authenticated else None,
                    app_name="sentence_explain",
                    topic=sentence[:50] if sentence else "Image explanation",
                    input_type="image" if image else "text",
                    time_spent=30,
                    outcome="completed"
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Streaming error: {e}")
                # We can't change status code once streaming starts, so we just stop.
                pass

        return StreamingHttpResponse(event_stream(), content_type='text/plain')

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"AI Connection error: {e}")
        return JsonResponse({"error": "Service Unavailable"}, status=503)
