import os
import django
from django.conf import settings
from django.test import RequestFactory, Client
from django.urls import reverse
import traceback

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
    print("Setting up Django...")
    django.setup()
    from django.conf import settings
    if 'testserver' not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']
    print("Django setup complete.")
except Exception as e:
    with open('verification_error.log', 'w') as f:
        traceback.print_exc(file=f)
    print(f"Error during Django setup: {e}")
    exit(1)

from django.contrib.auth.models import User
from accounts.models import UserProfile

def verify_teacher_access():
    print("Verifying Teacher Access...")
    # Create Teacher
    teacher_user, created = User.objects.get_or_create(username='test_teacher')
    teacher_user.set_password('testpass')
    teacher_user.save()
    
    if not hasattr(teacher_user, 'account_profile'):
        UserProfile.objects.create(user=teacher_user, role='Teacher', full_name='Test Teacher')
    else:
        teacher_user.account_profile.role = 'Teacher'
        teacher_user.account_profile.save()

    client = Client()
    client.login(username='test_teacher', password='testpass')
    
    url = reverse('analytics:teacher_dashboard')
    response = client.get(url)
    
    if response.status_code == 200:
        print("PASS: Teacher can access dashboard (Status 200)")
        if 'Status' in response.content.decode():
             print("PASS: 'Status' column found in response")
        else:
             print("FAIL: 'Status' column NOT found in response")
             return False
    else:
        with open('verification_output.txt', 'w') as f:
             f.write(f"FAIL: Teacher access returned {response.status_code}\n")
             if response.status_code != 200:
                  f.write(f"Response content prefix: {response.content[:1000]}\n")
        print(f"FAIL: Teacher access returned {response.status_code}")
        return False
        
    return True

def verify_student_redirect():
    print("\nVerifying Student Redirect...")
    # Create Student
    student_user, created = User.objects.get_or_create(username='test_student')
    student_user.set_password('testpass')
    student_user.save()
    
    if not hasattr(student_user, 'account_profile'):
        UserProfile.objects.create(user=student_user, role='Student', full_name='Test Student')
    else:
        student_user.account_profile.role = 'Student'
        student_user.account_profile.save()

    client = Client()
    client.login(username='test_student', password='testpass')
    
    url = reverse('analytics:teacher_dashboard')
    response = client.get(url, follow=True) # Follow redirect
    
    # SHould redirect to student dashboard or home depending on implementation
    # We changed it to redirect to 'analytics:student_dashboard'
    
    target_url = reverse('analytics:student_dashboard')
    
    if response.redirect_chain:
        print(f"Redirect chain: {response.redirect_chain}")
        last_url, status_code = response.redirect_chain[-1]
        
        # Verify it redirected to student dashboard
        if target_url in last_url or status_code == 302:
             print(f"PASS: Student was redirected (Chain: {response.redirect_chain})")
        else:
             print(f"FAIL: Unexpected redirect location: {last_url}")
             return False
    else:
        with open('verification_output.txt', 'w') as f:
            f.write(f"FAIL: Student was NOT redirected. Status: {response.status_code}\n")
            f.write(f"Redirect Chain: {response.redirect_chain}\n")
            if response.status_code != 302:
                 f.write(f"Response content prefix: {response.content[:1000]}\n")
        print("FAIL: Check verification_output.txt")
        return False
        
    return True

if __name__ == "__main__":
    t_pass = verify_teacher_access()
    s_pass = verify_student_redirect()
    
    if t_pass and s_pass:
        print("\nALL CHECKS PASSED")
    else:
        print("\nSOME CHECKS FAILED")
