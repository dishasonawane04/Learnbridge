from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import UserActivity
from accounts.models import UserProfile
from django.db import models
from django.db.models import Avg, Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from course.models import Course, CourseUnit, CourseMaterial, UserUnitCompletion

def home(request):
    return render(request, 'core/home.html')

@login_required
def dashboard(request):
    profile = None
    if hasattr(request.user, 'account_profile'):
        profile = request.user.account_profile
    elif hasattr(request.user, 'account_profile'):
        profile = request.user.account_profile
    else:
        # Fallback: create account profile if none exists
        UserProfile.objects.create(user=request.user, role='student')
        profile = request.user.account_profile

    # 1. Course Stats
    user_courses = Course.objects.filter(user=request.user).order_by('-created_at')
    total_courses = user_courses.count()
    
    # Calculate Total Units and Materials
    total_units = CourseUnit.objects.filter(course__user=request.user).count()
    total_materials = CourseMaterial.objects.filter(unit__course__user=request.user).count()

    # 2. Activity / Analytics (Still relevant for overview, but secondary)
    activities = UserActivity.objects.filter(user=request.user).order_by('-timestamp')
    total_time = activities.aggregate(Sum('time_spent'))['time_spent__sum'] or 0
    
    # 3. Streak Calculation
    streak = 0
    if activities.exists():
        activity_dates = activities.values_list('timestamp__date', flat=True).distinct()
        today = timezone.now().date()
        current_date = today
        last_activity_date = activity_dates[0]
        if last_activity_date == today or last_activity_date == (today - timedelta(days=1)):
            for date in activity_dates:
                if date == current_date:
                    streak += 1
                    current_date -= timedelta(days=1)
                elif date > current_date:
                    continue
                else:
                    break

    # 4. Course Progress / Mastery
    from course.models import UserUnitCompletion
    course_data = []
    for course in user_courses:
        units = course.units.all()
        completed_unit_ids = UserUnitCompletion.objects.filter(
            user=request.user, 
            unit__course=course
        ).values_list('unit_id', flat=True)
        
        completed_units_count = len(completed_unit_ids)
        progress = int((completed_units_count / units.count() * 100)) if units.exists() else 0
        
        course_data.append({
            'id': course.id,
            'title': course.title,
            'level': course.get_level_display(),
            'progress': progress,
            'units_count': units.count()
        })

    # 5. AI Recommendations (Keep relevant to topics)
    recommendations = []
    needs_revision = activities.filter(outcome='needs_revision').values('topic').distinct()[:2]
    for activity in needs_revision:
        recommendations.append({
            'topic': activity['topic'],
            'reason': "You struggled with this topic in your course materials. Let's master it.",
            'action': "Revise Now"
        })
    
    if len(recommendations) < 3:
        # Suggest something from recently created courses
        if user_courses.exists():
            latest_course = user_courses[0]
            recommendations.append({
                'topic': latest_course.title,
                'reason': f"Continue your progress in '{latest_course.title}'.",
                'action': "Continue Learning"
            })

    # 6. Recent Activity
    recent_activity = activities[:10]

    context = {
        'profile': profile,
        'total_courses': total_courses,
        'total_units': total_units,
        'total_materials': total_materials,
        'total_time': total_time // 60,
        'streak': streak,
        'course_data': course_data,
        'recommendations': recommendations,
        'recent_activity': recent_activity,
    }
    
    if profile and profile.role.lower() == 'teacher':
        return render(request, 'core/teacher_dashboard.html', context)
    return render(request, 'core/student_dashboard.html', context)

@login_required
def role_selection(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ['student', 'teacher']:
            UserProfile.objects.get_or_create(user=request.user, defaults={'role': role})
            return redirect('core:dashboard')
    return render(request, 'core/role_selection.html')
