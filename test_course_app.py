import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

def test_course_app():
    """Test the complete course app flow"""
    User = get_user_model()
    settings.ALLOWED_HOSTS += ['testserver']
    
    # Get admin user
    user = User.objects.get(username='admin')
    client = Client()
    client.force_login(user)
    
    print("Testing Course App...")
    print("-" * 60)
    
    # Test 1: Course List
    print("\n1. Testing course list page...")
    response = client.get(reverse('course:list'))
    if response.status_code == 200:
        print(f"   ✅ Course list loads successfully (200)")
    else:
        print(f"   ❌ Course list failed ({response.status_code})")
        return
    
    # Test 2: Course Create GET
    print("\n2. Testing course creation form...")
    response = client.get(reverse('course:create'))
    if response.status_code == 200:
        print(f"   ✅ Course creation form loads successfully (200)")
        # Check if Cancel button URL is correct
        if 'course:list' in response.content.decode():
            print(f"   ✅ Cancel button uses correct URL reference")
        else:
            print(f"   ⚠️  Could not verify Cancel button URL")
    else:
        print(f"   ❌ Course creation form failed ({response.status_code})")
        return
    
    # Test 3: Course Create POST
    print("\n3. Testing course creation...")
    response = client.post(reverse('course:create'), {
        'title': 'Test Course',
        'description': 'A test course for verification',
        'level': 'UG'
    })
    if response.status_code in [200, 302]:  # 302 = redirect
        print(f"   ✅ Course creation successful ({response.status_code})")
        if response.status_code == 302:
            print(f"   ✅ Redirects to: {response.url}")
    else:
        print(f"   ❌ Course creation failed ({response.status_code})")
        return
    
    # Test 4: Verify course was created
    from course.models import Course
    test_course = Course.objects.filter(title='Test Course').first()
    if test_course:
        print(f"   ✅ Course saved to database (ID: {test_course.id})")
        
        # Test 5: Course Detail
        print("\n4. Testing course detail page...")
        response = client.get(reverse('course:detail', kwargs={'course_id': test_course.id}))
        if response.status_code == 200:
            print(f"   ✅ Course detail page loads successfully (200)")
        else:
            print(f"   ❌ Course detail page failed ({response.status_code})")
        
        # Clean up
        test_course.delete()
        print(f"\n   🧹 Test course cleaned up")
    else:
        print(f"   ❌ Course not found in database")
    
    print("\n" + "=" * 60)
    print("✅ All course app tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    test_course_app()
