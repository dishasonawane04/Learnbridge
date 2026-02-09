import os
import django
from django.urls import reverse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

def check_url(name, *args, **kwargs):
    try:
        url = reverse(name, *args, **kwargs)
        print(f"[OK] {name} -> {url}")
    except Exception as e:
        print(f"[FAIL] {name} -> {e}")

print("Checking URLs...")
check_url('home')
check_url('dashboard')
check_url('course:list')
check_url('quiz_subjects')
check_url('study_plan')
check_url('sentence_explain')
check_url('notes')
check_url('accounts:login')
check_url('accounts:signup')
check_url('accounts:logout')
check_url('ai_tutor:tutor_home')
check_url('learning_support:support_home')
check_url('flashcard_generator:flashcard_home')
check_url('prerequisite_checker:home')
check_url('letter_of_recommendation_generator:letter_dashboard')
check_url('analytics:student_dashboard')

print("Done.")
