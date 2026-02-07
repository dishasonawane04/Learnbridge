#!/usr/bin/env python
"""
Comprehensive AI Tools Integration Test
Tests all AI tools with unit context
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from course.models import Course, CourseUnit
from django.conf import settings

def test_ai_tools_integration():
    """Test all AI tools work with unit context"""
    User = get_user_model()
    settings.ALLOWED_HOSTS += ['testserver']
    
    # Get admin user
    user = User.objects.get(username='admin')
    client = Client()
    client.force_login(user)
    
    print("=" * 80)
    print("AI TOOLS INTEGRATION TEST")
    print("=" * 80)
    
    # Create test course and unit
    print("\n📚 Creating test course and unit...")
    course = Course.objects.create(
        user=user,
        title="AI Tools Test Course",
        description="Testing AI tools integration",
        level="UG"
    )
    
    unit = CourseUnit.objects.create(
        course=course,
        title="Introduction to Machine Learning",
        overview="Learn the fundamentals of ML including supervised and unsupervised learning",
        content="Detailed notes about ML algorithms, neural networks, and deep learning",
        order=1
    )
    print(f"  ✅ Created course (ID: {course.id}) and unit (ID: {unit.id})")
    
    # Test AI Tools
    ai_tools = [
        {
            'name': 'AI Tutor',
            'url': reverse('ai_tutor:start_unit_chat', kwargs={'unit_id': unit.id}),
            'expected_status': 200 # Returns chat interface directly
        },
        {
            'name': 'Learning Support',
            'url': reverse('learning_support:start_unit_support', kwargs={'unit_id': unit.id}),
            'expected_status': 302 # Redirects to support interface
        },
        {
            'name': 'Flashcard Generator',
            'url': reverse('flashcard_generator:generate_from_unit', kwargs={'unit_id': unit.id}),
            'expected_status': 302 # Redirects to deck view
        },
        {
            'name': 'Quiz Generator',
            'url': reverse('quiz:start_unit_quiz', kwargs={'unit_id': unit.id}),
            'expected_status': 302 # Redirects to quiz interface
        },
        {
            'name': 'Notes Generator',
            'url': reverse('notes:generate_unit_notes', kwargs={'unit_id': unit.id}),
            'expected_status': 302 # Redirects to notes view
        },
        {
            'name': 'Study Plan Generator',
            'url': reverse('generator:generate_unit_plan', kwargs={'unit_id': unit.id}),
            'expected_status': 302 # Redirects to plan view
        },
    ]
    
    print("\n🤖 Testing AI Tools with Unit Context:")
    print("-" * 80)
    
    for tool in ai_tools:
        try:
            # First check if the URL resolves (since some might not be implemented yet)
            from django.urls import resolve
            try:
                resolve(tool['url'])
            except:
                print(f"  ❌ {tool['name']}: URL remains unimplemented")
                continue

            response = client.get(tool['url'])
            status = "✅" if response.status_code == tool['expected_status'] else "❌"
            print(f"  {status} {tool['name']}: {response.status_code}")
            
            # If it's a redirect, we can follow it or just trust the 302
            if response.status_code == 302:
                 redirect_url = response['Location']
                 print(f"     ➔ Redirected to: {redirect_url}")
        except Exception as e:
            print(f"  ❌ {tool['name']}: ERROR - {str(e)[:60]}")
    
    # Cleanup
    course.delete()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_ai_tools_integration()
