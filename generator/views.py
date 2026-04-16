from django.shortcuts import render
from django.conf import settings
import ollama
import markdown
from asgiref.sync import sync_to_async
from core.utils import log_activity

from datetime import datetime

async def study_plan(request):
    plan = None
    topic = request.GET.get('topic', '')
    hours = request.GET.get('hours', '2')
    exam_date = request.GET.get('exam_date', '')
    course_id = request.GET.get('course_id', '')

    if request.method == "POST":
        topic = request.POST.get("topic", topic)
        hours = request.POST.get("hours", hours)
        exam_date = request.POST.get("exam_date", exam_date)
        course_id = request.POST.get("course_id", course_id)
        
        # --- CENTRALIZED CONTEXT INJECTION ---
        from course.services.context_provider import get_course_context
        
        if not course_id:
            course_id = request.session.get("active_course_id")
            
        context_text = get_course_context(request.user, course_id)
        
        language = request.POST.get("language", "English")
        
        # Calculate days until exam
        days_until_exam = 7 # Default
        if exam_date:
            try:
                exam_date_obj = datetime.strptime(exam_date, "%Y-%m-%d").date()
                today = datetime.now().date()
                days_until_exam = (exam_date_obj - today).days
                if days_until_exam <= 0:
                    days_until_exam = 1
                
                # Update Readiness if course_id is present
                if course_id:
                    from course.models import Course, UserCourseReadiness
                    
                    @sync_to_async
                    def update_exam_goal():
                        try:
                            course = Course.objects.get(id=course_id)
                            readiness, _ = UserCourseReadiness.objects.get_or_create(
                                user=request.user, 
                                course=course
                            )
                            readiness.exam_date_goal = exam_date_obj
                            readiness.save()
                        except Course.DoesNotExist:
                            pass
                    await update_exam_goal()
            except ValueError:
                pass

        system_prompt = (
            "You are an academic AI assistant. "
            "Use ONLY the following study material to generate the study plan. "
            f"\n--- COURSE NOTES ---\n{context_text}\n---------------------\n"
        )

        task_prompt = f"""task:
        Generate a detailed study plan in {language} for the topic: '{topic}'.
        The student has {days_until_exam} days until their exam.
        The student can dedicate {hours} hours per day to studying.
        
        Analyze the COURSE NOTES above and:
        1. Identify important topics and concepts.
        2. Estimate how much time each topic needs based on the {hours} hours/day limit.
        3. Distribute the topics across the {days_until_exam} days.
        4. Include Revision days and Practice/Quiz days before the exam.
        
        FORMAT YOUR OUTPUT EXACTLY AS FOLLOWS (with your generated content):
        # Study Plan: {topic} ({days_until_exam} Days, {hours} hrs/day)
        
        ## Day 1-2: [Topic Title] ({int(hours)*2} hours)
        - Subtopic 1
        - Subtopic 2
        
        ## Day 3: [Topic Title] ({hours} hours)
        ...
        
        ## Day {days_until_exam - 1}: Practice Quiz
        ## Day {days_until_exam}: Final Revision
        
        Ensure the response is strictly in {language}.
        """
        
        final_prompt = f"{system_prompt}\n\n{task_prompt}"

        client = ollama.AsyncClient()

        try:
            res = await client.chat(
                model=settings.OLLAMA_MODEL_TEXT,
                messages=[{'role': 'user', 'content': final_prompt}]
            )
            plan = res['message']['content']
        except Exception as e:
            plan = f"Error generating study plan: {str(e)}"

        # Convert plan to HTML if it exists and no error occurred
        plan_html = ""
        if plan and not plan.startswith("Error"):
            plan_html = markdown.markdown(plan, extensions=['fenced_code', 'tables'])
        else:
            plan_html = plan

        # Log Activity
        await sync_to_async(log_activity)(
            user=request.user,
            app_name="study_plan",
            topic=topic,
            input_type="text",
            time_spent=120, # Estimation for planning
            outcome="completed"
        )

    return await sync_to_async(render)(request, "generator/plan.html", {
        "plan": plan,
        "plan_html": plan_html if 'plan_html' in locals() else "",
        "topic": topic,
        "hours": hours
    })

def generate_unit_plan(request, unit_id):
    """Initializes study plan generation from a Course Unit."""
    from course.models import CourseUnit
    from django.shortcuts import get_object_or_404, redirect
    from django.urls import reverse
    unit = get_object_or_404(CourseUnit, id=unit_id)
    return redirect(f"{reverse('generator:study_plan')}?unit_id={unit.id}&topic={unit.title}")

def image_report_view(request):
    """
    Independent feature to generate an AI report directly from an uploaded image.
    Uses OCR for text extraction, then falls back to Ollama Vision directly if OCR fails.
    """
    from django.core.files.storage import FileSystemStorage
    from course.utils.extraction import extract_text_from_path
    import os, base64, json, requests as http_requests

    report = None
    report_html = None
    error_msg = None

    if request.method == "POST":
        uploaded_file = request.FILES.get("image_file")
        if not uploaded_file:
            error_msg = "Please upload an image."
        else:
            try:
                fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads'))
                filename = fs.save(uploaded_file.name, uploaded_file)
                file_path = fs.path(filename)

                language = request.session.get("ai_language", "English")

                # --- Stage 1: OCR-based extraction ---
                extracted_text = extract_text_from_path(file_path)
                ocr_ok = (
                    extracted_text
                    and len(extracted_text.strip()) >= 10
                    and "Unable to detect text" not in extracted_text
                )

                if ocr_ok:
                    # OCR succeeded → generate report from extracted text via direct call
                    system_prompt = (
                        "You are an expert analytical AI. Your objective is to extract meaning from the raw OCR text "
                        "of an uploaded image and generate a highly professional, structured report. "
                        "Organize your report using Markdown formatting (with ## headings). "
                        "Include the following sections clearly: 'Overview', 'Key Observations', "
                        "'Extracted Details', and 'Conclusion'. "
                        f"Format the entire response in {language}."
                    )
                    task_prompt = (
                        "Please analyze the following raw text extracted from an image and generate a "
                        "structured analytical report:\n\nRAW TEXT:\n" + extracted_text[:3000]
                    )
                    text_model = getattr(settings, 'OLLAMA_MODEL_TEXT', 'tinyllama:latest')
                    try:
                        resp = http_requests.post(
                            f"{settings.OLLAMA_BASE_URL}/api/generate",
                            json={
                                "model": text_model,
                                "prompt": f"{system_prompt}\n\nStudent: {task_prompt}\nAI:",
                                "stream": False,
                                "options": {"temperature": 0.3, "num_predict": 800}
                            },
                            timeout=90
                        )
                        resp.raise_for_status()
                        report = resp.json().get('response', '').strip()
                        if not report:
                            error_msg = "The AI model returned an empty response. Please try again."
                    except http_requests.exceptions.Timeout:
                        error_msg = "The AI took too long to respond (>90s). Try uploading a shorter document."
                    except http_requests.exceptions.ConnectionError:
                        error_msg = "Could not connect to AI. Make sure Ollama is running (`ollama serve`)."
                    except Exception as e:
                        error_msg = f"AI report generation failed: {e}"
                else:
                    # --- Stage 2: Direct Ollama Vision fallback ---
                    # Send the image directly to the vision model to both read and analyse it.
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                        error_msg = (
                            "Could not extract text from this file. "
                            "Please upload a clearer image (PNG, JPG, or JPEG)."
                        )
                    else:
                        try:
                            with open(file_path, "rb") as img_file:
                                encoded_image = base64.b64encode(img_file.read()).decode('utf-8')

                            vision_prompt = (
                                f"You are an expert analytical AI. Look at this image carefully and generate "
                                f"a highly professional, structured report in {language}. "
                                "Use Markdown formatting with these sections: "
                                "## Overview, ## Key Observations, ## Extracted Details, ## Conclusion. "
                                "Transcribe any visible text and analyse the content thoroughly."
                            )
                            vision_model = getattr(settings, 'OLLAMA_MODEL_VISION', 'llava:latest')
                            payload = {
                                "model": vision_model,
                                "prompt": vision_prompt,
                                "images": [encoded_image],
                                "stream": False,
                                "options": {"temperature": 0.3, "num_predict": 1500}
                            }
                            resp = http_requests.post(
                                f"{settings.OLLAMA_BASE_URL}/api/generate",
                                json=payload,
                                timeout=60
                            )
                            resp.raise_for_status()
                            report = resp.json().get('response', '').strip()
                            if not report:
                                error_msg = (
                                    "The AI vision model returned an empty response. "
                                    "Please ensure the vision model (llava) is installed: "
                                    "run `ollama pull llava` in your terminal."
                                )
                        except http_requests.exceptions.ConnectionError:
                            error_msg = (
                                "Could not connect to the AI service. "
                                "Please make sure Ollama is running (`ollama serve`)."
                            )
                        except Exception as vision_err:
                            error_msg = (
                                f"OCR could not read the image and the AI vision fallback also failed: "
                                f"{vision_err}. Try a clearer, higher-resolution image."
                            )

                # --- Render the report if we got one ---
                if report and not report.startswith("Error"):
                    report_html = markdown.markdown(report, extensions=['fenced_code', 'tables'])
                elif report and report.startswith("Error") and not error_msg:
                    error_msg = f"AI service error: {report}"
                    report = None

            except Exception as e:
                error_msg = f"An unexpected error occurred: {str(e)}"

    return render(request, "generator/image_report.html", {
        "report_html": report_html,
        "error_msg": error_msg
    })
