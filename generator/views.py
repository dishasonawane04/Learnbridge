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
        
        from course.services.ai_context import get_course_context
        course_id = request.GET.get('course_id')
        context = ""
        if course_id:
            context = get_course_context(course_id=course_id)
            context = f"\nUse the following COURSE CONTEXT (materials and units) to structure this plan:\n{context}\n"

        client = ollama.AsyncClient()

        prompt = f"""
        Generate a detailed 7-day study plan for the topic: '{topic}'. 
        The student can dedicate {hours} hours per week.
        {context}
        
        FORMAT:
        # Study Plan: [Topic] ({hours} hrs/week)
        
        ## Day 1: Introduction
        - Task 1 (Duration)
        - Task 2 (Duration)
        
        ... and so on for 7 days.
        Include specific concepts and a mini-project for Day 7.
        """

        try:
            res = await client.chat(
                model=settings.OLLAMA_MODEL_TEXT,
                messages=[{'role': 'user', 'content': prompt}]
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
