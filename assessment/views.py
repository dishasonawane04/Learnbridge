import os
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import ollama
from asgiref.sync import sync_to_async
from core.utils import log_activity

async def learning_support(request):
    response = None
    image_url = None
    topic = request.GET.get('topic', 'General Doubt')

    if request.method == "POST":
        doubt = request.POST.get("doubt")
        image = request.FILES.get("image")
        
        client = ollama.AsyncClient()

        from course.services.context_provider import get_course_context
        course_id = request.session.get("active_course_id") or request.GET.get('course_id')
        context = ""
        if course_id:
            context_text = get_course_context(request.user, course_id=course_id)
            context = f"\nUse the following COURSE CONTEXT for reference:\n{context_text}\n"

        if image:
            def save_file(img):
                fs = FileSystemStorage()
                filename = fs.save(img.name, img)
                return fs.url(filename), fs.path(filename)
            
            image_url, image_path = await sync_to_async(save_file)(image)

            try:
                # Simplified LLaVA explanation for Learning Support
                res = await client.chat(
                    model=settings.OLLAMA_MODEL_VISION,
                    messages=[{
                        'role': 'user',
                        'content': f"Provide a simplified, step-by-step explanation for this doubt: {doubt or ''}. {context} Focus on clarity and basics.",
                        'images': [image_path]
                    }]
                )
                response = res['message']['content']
            except Exception as e:
                response = f"Error: {str(e)}"
        
        elif doubt:
            try:
                res = await client.chat(
                    model=settings.OLLAMA_MODEL_TEXT,
                    messages=[{
                        'role': 'user',
                        'content': f"Simplify this concept: {doubt}. {context} Use an analogy and a step-by-step breakdown."
                    }]
                )
                response = res['message']['content']
            except Exception as e:
                response = f"Error: {str(e)}"

        # Log Activity
        await sync_to_async(log_activity)(
            user=request.user,
            app_name="learning_support",
            topic=topic,
            input_type="image" if image else "text",
            time_spent=45,
            outcome="completed"
        )

    return await sync_to_async(render)(request, "assessment/learning_support.html", {
        "response": response,
        "image_url": image_url,
        "topic": topic
    })
