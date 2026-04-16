import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from core.ai.services import CourseContextEngine
import logging

try:
    print("Testing ask_course_ai_raw...")
    response = CourseContextEngine.ask_course_ai_raw(
        user_msg="Please analyze the following raw text: Hello World", 
        system_prompt="You are an expert analytical AI."
    )
    print("RESPONSE:")
    print(response)
except Exception as e:
    import traceback
    traceback.print_exc()
