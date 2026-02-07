import os
import django
from django.conf import settings
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

def check_urls():
    # Allow testserver for Client requests
    settings.ALLOWED_HOSTS += ['testserver']
    
    User = get_user_model()
    # Ensure admin user exists for testing
    user = User.objects.get(username='admin')
    client = Client()
    client.force_login(user)

    urls_to_test = [
        ('/', 'Home'),
        (reverse('core:dashboard'), 'Dashboard'),
        (reverse('course:list'), 'Course List'),
        (reverse('ai_tutor:tutor_home'), 'AI Tutor Home'),
        (reverse('quiz:quiz_subjects'), 'Quiz Subjects'),
        (reverse('notes:notes_list'), 'Notes List'),
        (reverse('analytics:student_dashboard'), 'Analytics Dashboard'),
        # Add more as discovered
    ]

    print(f"{'URL':<40} | {'Status':<10} | {'Result':<10}")
    print("-" * 65)

    errors = []

    for url, name in urls_to_test:
        try:
            response = client.get(url)
            status = response.status_code
            result = "✅ OK" if status == 200 else f"❌ {status}"
            print(f"{name:<40} | {status:<10} | {result:<10}")
            
            if status != 200:
                errors.append(f"{name} returned {status}")
                
        except Exception as e:
            print(f"{name:<40} | {'ERR':<10} | ❌ EXCEPTION")
            print(f"Error: {str(e)}")
            errors.append(f"{name} crashed: {str(e)}")

    if not errors:
        print("\n🎉 All critical pages are loading correctly!")
    else:
        print(f"\n⚠️ Found {len(errors)} errors.")

if __name__ == "__main__":
    check_urls()
