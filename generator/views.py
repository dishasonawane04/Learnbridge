from django.shortcuts import render
from django.conf import settings
import ollama
import markdown
from asgiref.sync import sync_to_async
from core.utils import log_activity

async def study_plan(request):
    plan = None
    topic = request.GET.get('topic', '')
    hours = request.GET.get('hours', '5')

    if request.method == "POST":
        topic = request.POST.get("topic", topic)
        hours = request.POST.get("hours", hours)
        
        # --- CENTRALIZED CONTEXT INJECTION ---
        from course.services.context_provider import get_course_context
        
        course_id = request.session.get("active_course_id") or request.GET.get('course_id') or request.POST.get('course_id')
        
        context_text = get_course_context(request.user, course_id)
        
        system_prompt = (
            "You are an academic AI assistant. "
            "Use ONLY the following study material to generate the study plan. "
            f"\n--- COURSE NOTES ---\n{context_text}\n---------------------\n"
        )

        task_prompt = f"""task:
        Generate a detailed 7-day study plan for the topic: '{topic}'. 
        The student can dedicate {hours} hours per week.
        
        FORMAT:
        # Study Plan: [Topic] ({hours} hrs/week)
        
        ## Day 1: Introduction
        - Task 1 (Duration)
        - Task 2 (Duration)
        
        ... and so on for 7 days.
        Include specific concepts and a mini-project for Day 7.
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
