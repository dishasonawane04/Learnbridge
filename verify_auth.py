import os
import sys

# Setup Django environment
sys.path.append('d:\\DISHA\\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')

import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from accounts.models import UserProfile
from letter_of_recommendation_generator.views import letter_dashboard
from learnbridge.views import dashboard

def setup_users():
    print("Setting up test users...")
    # Create Teacher
    teacher_user, _ = User.objects.get_or_create(username='test_teacher')
    UserProfile.objects.get_or_create(user=teacher_user, defaults={'role': 'Teacher', 'full_name': 'Test Teacher'})

    # Create Student
    student_user, _ = User.objects.get_or_create(username='test_student')
    UserProfile.objects.get_or_create(user=student_user, defaults={'role': 'Student', 'full_name': 'Test Student'})
    
    return teacher_user, student_user

def test_access_control(teacher, student):
    factory = RequestFactory()
    
    print("\nTesting Access Control for LOR Dashboard...")
    
    # Test Teacher Access
    req_teacher = factory.get('/lor/')
    req_teacher.user = teacher
    setattr(req_teacher, 'session', 'session')
    messages = FallbackStorage(req_teacher)
    setattr(req_teacher, '_messages', messages)
    
    resp_teacher = letter_dashboard(req_teacher)
    
    # Depending on how decorating works, a redirect happens if checks fail.
    # A successful view return usually means access granted.
    # The view returns a TemplateResponse (status 200) on success.
    
    if resp_teacher.status_code == 200:
        print("PASS: Teacher accessed LOR Dashboard.")
    else:
        print(f"FAIL: Teacher denied access. Status: {resp_teacher.status_code}")

    # Test Student Access
    req_student = factory.get('/lor/')
    req_student.user = student
    setattr(req_student, 'session', 'session')
    messages = FallbackStorage(req_student)
    setattr(req_student, '_messages', messages)

    resp_student = letter_dashboard(req_student)
    
    # Expect redirect (302) because of @teacher_required
    if resp_student.status_code == 302:
        print("PASS: Student redirected (Access Denied).")
    else:
        print(f"FAIL: Student accessed LOR Dashboard. Status: {resp_student.status_code}")

def test_dashboard_filtering(teacher, student):
    factory = RequestFactory()
    print("\nTesting Dashboard App Filtering...")
    
    # Teacher Dashboard
    req_t = factory.get('/')
    req_t.user = teacher
    resp_t = dashboard(req_t)
    
    # We need to render response to check content, but simpler to check context if we could.
    # Since dashboard returns HttpResponse with rendered content, we check substring.
    # LOR Generator card has link "/lor/"
    
    if b'/lor/' in resp_t.content:
        print("PASS: Teacher dashboard shows LOR link.")
    else:
        print("FAIL: Teacher dashboard missing LOR link.")

    # Student Dashboard
    req_s = factory.get('/')
    req_s.user = student
    resp_s = dashboard(req_s)
    
    if b'/lor/' not in resp_s.content:
        print("PASS: Student dashboard HIDES LOR link.")
    else:
        print("FAIL: Student dashboard SHOWS LOR link (Should be hidden).")

if __name__ == "__main__":
    t, s = setup_users()
    test_access_control(t, s)
    test_dashboard_filtering(t, s)
