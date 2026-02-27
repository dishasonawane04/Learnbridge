from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import UserActivity
from accounts.models import UserProfile
from django.db import models
from django.db.models import Avg, Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from course.models import Course, CourseUnit, CourseMaterial, UserUnitCompletion

from django.contrib import messages

def home(request):
    return render(request, 'core/home.html')

@login_required
def set_active_course(request):
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        if course_id:
            request.session['active_course_id'] = course_id
            # Set is_active flag in DB
            Course.objects.filter(user=request.user).update(is_active=False)
            Course.objects.filter(user=request.user, id=course_id).update(is_active=True)
            messages.success(request, f"Active course updated.")
    
    next_url = request.POST.get('next')
    if not next_url:
        if course_id:
            return redirect('course:course_dashboard', course_id=course_id)
        next_url = request.META.get('HTTP_REFERER') or 'core:dashboard'
    
    return redirect(next_url)

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
    
    # Ensure at least one course is active if none is set
    if user_courses.exists() and not user_courses.filter(is_active=True).exists():
        first_course = user_courses.first()
        first_course.is_active = True
        first_course.save()
        request.session['active_course_id'] = str(first_course.id)

    total_courses = user_courses.count()
    
    # Calculate Total Units and Materials
    total_units = CourseUnit.objects.filter(course__user=request.user).count()
    total_materials = CourseMaterial.objects.filter(
        Q(unit__course__user=request.user) | Q(course__user=request.user)
    ).distinct().count()

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

    # 7. Recent Activity (Context processor handles active course)
    recent_activity = activities[:10]

    context = {
        'profile': profile,
        'active_course': user_courses.filter(is_active=True).first(),
        'total_courses': total_courses,
        'total_units': total_units,
        'total_materials': total_materials,
        'total_time': total_time // 60,
        'streak': streak,
        'course_data': course_data,
        'recommendations': recommendations,
        'recent_activity': recent_activity,
    }
    
    if profile and profile.role.lower() == 'faculty':
        return render(request, 'core/faculty_dashboard.html', context)
    return render(request, 'core/student_dashboard.html', context)

@login_required
def role_selection(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ['student', 'faculty']:
            UserProfile.objects.get_or_create(user=request.user, defaults={'role': role})
            return redirect('core:dashboard')
    return render(request, 'core/role_selection.html')

@login_required
def active_course_api(request):
    """
    API endpoint to return the current user's active course.
    """
    active_course = Course.objects.filter(user=request.user, is_active=True).first()
    if not active_course:
        # Fallback to session if is_active is not yet set
        course_id = request.session.get('active_course_id')
        if course_id:
            active_course = Course.objects.filter(user=request.user, id=course_id).first()
    
    if active_course:
        return JsonResponse({
            'status': 'success',
            'id': active_course.id,
            'title': active_course.title,
            'url': f"/course/{active_course.id}/"
        })
    return JsonResponse({'status': 'null'}, safe=False)
