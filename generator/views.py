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
