import os
import django
from django.template.loader import render_to_string
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

def verify_templates():
    print("Verifying templates...")
    try:
        # Verify base.html
        render_to_string('base.html', {'request': None, 'user': None, 'messages': []})
        print("✅ base.html passed syntax check.")

        # Verify course_list.html
        # Needs a 'courses' context
        class MockUser:
            is_staff = False
            is_superuser = False
            username = "testuser"
            is_authenticated = True
            class core_profile:
                role = 'student'

        class MockRequest:
            user = MockUser()
            resolver_match = type('obj', (object,), {'url_name': 'course_list', 'app_name': 'course'})

        render_to_string('course/course_list.html', {'courses': [], 'request': MockRequest()})
        print("✅ course/course_list.html passed syntax check (empty list).")
        
    except Exception as e:
        print(f"❌ Template Error: {e}")

if __name__ == "__main__":
    verify_templates()
