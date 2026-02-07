import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from course.models import Course, CourseUnit

def test_course_refactoring():
    """Comprehensive test for course app refactoring"""
    User = get_user_model()
    settings.ALLOWED_HOSTS += ['testserver']
    
    # Get admin user
    user = User.objects.get(username='admin')
    client = Client()
    client.force_login(user)
    
    print("=" * 70)
    print("COURSE APP REFACTORING - COMPREHENSIVE TEST")
    print("=" * 70)
    
    # Test 1: Course List
    print("\n1. Testing course list page...")
    response = client.get(reverse('course:list'))
    assert response.status_code == 200, f"Failed: {response.status_code}"
    print("   ✅ Course list loads successfully")
    
    # Test 2: Course Create
    print("\n2. Testing course creation...")
    response = client.post(reverse('course:create'), {
        'title': 'Test Refactoring Course',
        'description': 'Testing the refactored course app',
        'level': 'UG'
    })
    assert response.status_code in [200, 302], f"Failed: {response.status_code}"
    print("   ✅ Course creation successful")
    
    # Get the created course
    course = Course.objects.filter(title='Test Refactoring Course').first()
    assert course is not None, "Course not found in database"
    print(f"   ✅ Course saved to database (ID: {course.id})")
    
    # Test 3: Course Detail
    print("\n3. Testing course detail page...")
    response = client.get(reverse('course:detail', kwargs={'course_id': course.id}))
    assert response.status_code == 200, f"Failed: {response.status_code}"
    assert 'Add Unit' in response.content.decode(), "Add Unit button not found"
    print("   ✅ Course detail page loads with Add Unit button")
    
    # Test 4: Unit Creation Form
    print("\n4. Testing unit creation form...")
    response = client.get(reverse('course:unit_create', kwargs={'course_id': course.id}))
    assert response.status_code == 200, f"Failed: {response.status_code}"
    print("   ✅ Unit creation form loads successfully")
    
    # Test 5: Create Unit with Overview
    print("\n5. Testing unit creation with overview field...")
    response = client.post(reverse('course:unit_create', kwargs={'course_id': course.id}), {
        'title': 'Introduction to Testing',
        'overview': 'Learn the fundamentals of software testing and quality assurance',
        'content': 'Detailed notes about testing methodologies',
        'order': 1
    })
    assert response.status_code in [200, 302], f"Failed: {response.status_code}"
    print("   ✅ Unit creation successful")
    
    # Verify unit was created with overview
    unit = CourseUnit.objects.filter(course=course, title='Introduction to Testing').first()
    assert unit is not None, "Unit not found in database"
    assert unit.overview == 'Learn the fundamentals of software testing and quality assurance', "Overview not saved"
    print(f"   ✅ Unit saved with overview field (ID: {unit.id})")
    
    # Test 6: Unit Detail Page
    print("\n6. Testing unit detail page...")
    response = client.get(reverse('course:unit_detail', kwargs={'unit_id': unit.id}))
    assert response.status_code == 200, f"Failed: {response.status_code}"
    assert 'Edit Unit' in response.content.decode(), "Edit Unit button not found"
    assert unit.overview in response.content.decode(), "Overview not displayed"
    print("   ✅ Unit detail page loads with overview and edit button")
    
    # Test 7: Unit Edit Form
    print("\n7. Testing unit edit form...")
    response = client.get(reverse('course:unit_edit', kwargs={'unit_id': unit.id}))
    assert response.status_code == 200, f"Failed: {response.status_code}"
    assert unit.overview in response.content.decode(), "Overview not pre-filled"
    print("   ✅ Unit edit form loads with existing data")
    
    # Test 8: Update Unit
    print("\n8. Testing unit update...")
    response = client.post(reverse('course:unit_edit', kwargs={'unit_id': unit.id}), {
        'title': 'Introduction to Testing (Updated)',
        'overview': 'Updated overview with more details',
        'content': unit.content,
        'order': unit.order
    })
    assert response.status_code in [200, 302], f"Failed: {response.status_code}"
    
    # Verify update
    unit.refresh_from_db()
    assert 'Updated' in unit.title, "Title not updated"
    assert 'Updated overview' in unit.overview, "Overview not updated"
    print("   ✅ Unit updated successfully")
    
    # Test 9: AI Context Service
    print("\n9. Testing AI context service...")
    from course.services.ai_context import get_system_prompt
    system_prompt = get_system_prompt(course, unit)
    assert course.title in system_prompt, "Course title not in prompt"
    assert unit.title in system_prompt, "Unit title not in prompt"
    assert unit.overview in system_prompt, "Unit overview not in prompt"
    print("   ✅ AI context service uses overview field correctly")
    
    # Test 10: Permission Checks
    print("\n10. Testing permission checks...")
    # Create a regular user
    regular_user = User.objects.create_user(username='testuser', password='testpass')
    client.force_login(regular_user)
    
    # Should not see Add Unit button
    response = client.get(reverse('course:detail', kwargs={'course_id': course.id}))
    assert 'Add Unit' not in response.content.decode(), "Regular user should not see Add Unit button"
    
    # Should not be able to create unit
    response = client.get(reverse('course:unit_create', kwargs={'course_id': course.id}))
    assert response.status_code == 302, "Regular user should be redirected"
    print("   ✅ Permission checks working correctly")
    
    # Cleanup
    regular_user.delete()
    course.delete()
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED - COURSE APP REFACTORING SUCCESSFUL!")
    print("=" * 70)

if __name__ == "__main__":
    test_course_refactoring()
