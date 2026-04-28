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

def _get_dashboard_context(request):
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
    if request.user.is_staff or request.user.is_superuser:
        user_courses = Course.objects.filter(is_deleted=False).order_by('-created_at')
    else:
        user_courses = Course.objects.filter(user=request.user, is_deleted=False).order_by('-created_at')
    
    # Ensure at least one course is active if none is set
    if user_courses.exists() and not user_courses.filter(is_active=True).exists():
        first_course = user_courses.first()
        first_course.is_active = True
        first_course.save()
        request.session['active_course_id'] = str(first_course.id)

    total_courses = user_courses.count()
    
    # Calculate Total Units and Materials
    if request.user.is_staff or request.user.is_superuser:
        total_units = CourseUnit.objects.all().count()
        total_materials = CourseMaterial.objects.all().count()
    else:
        total_units = CourseUnit.objects.filter(course__user=request.user).count()
        total_materials = CourseMaterial.objects.filter(
            Q(unit__course__user=request.user) | Q(course__user=request.user)
        ).distinct().count()

    # 2. Activity / Analytics (Still relevant for overview, but secondary)
    activities = UserActivity.objects.filter(user=request.user).order_by('-timestamp')
    total_time = activities.aggregate(Sum('time_spent'))['time_spent__sum'] or 0
    
    # Calculate Topic Distribution for Chart
    topic_counts = activities.values('topic').annotate(count=Count('topic')).order_by('-count')[:4]
    topic_dist = list(topic_counts)
    if not topic_dist:
        topic_dist = [{'topic': 'General', 'count': 1}]

    # 3. Streak Calculation
    # ... (rest of the calculation remains same)
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
        'active_course': user_courses.filter(is_active=True).first(),
        'total_courses': total_courses,
        'total_units': total_units,
        'total_materials': total_materials,
        'total_time': total_time // 60,
        'streak': streak,
        'course_data': course_data,
        'recommendations': recommendations,
        'recent_activity': recent_activity,
        'topic_dist': topic_dist,
    }
    return context, profile

@login_required
def dashboard_redirect(request):
    from accounts.models import UserProfile
    from django.contrib import messages
    profile = UserProfile.objects.filter(user=request.user).first()
    
    if profile:
        raw_role = profile.role
        clean_role = str(raw_role).lower().strip()
        if clean_role == 'faculty' or request.user.is_staff:
            return redirect('core:faculty_dashboard')
    elif request.user.is_staff:
        return redirect('core:faculty_dashboard')
            
    return redirect('core:student_dashboard')

from functools import wraps

def faculty_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        from accounts.models import UserProfile
        profile = UserProfile.objects.filter(user=request.user).first()
        is_faculty = (profile and str(profile.role).lower().strip() == 'faculty') or request.user.is_staff
        if is_faculty:
            return view_func(request, *args, **kwargs)
        messages.error(request, "You do not have permission to access the faculty dashboard.")
        return redirect('core:student_dashboard')
    return _wrapped_view

@login_required
def student_dashboard(request):
    context, profile = _get_dashboard_context(request)
    
    from course.models import TaskSubmission
    from django.utils import timezone
    
    user_submissions = TaskSubmission.objects.filter(student=request.user).select_related('assignment', 'assignment__course').order_by('assignment__deadline')
    
    now = timezone.now()
    for sub in user_submissions:
        if sub.status in ['pending', 'in_progress'] and sub.assignment.deadline and now > sub.assignment.deadline:
            sub.status = 'overdue'
            sub.save()
            
    context['pending_tasks'] = [s for s in user_submissions if s.status in ['pending', 'in_progress', 'overdue']]
    context['completed_tasks'] = [s for s in user_submissions if s.status in ['completed', 'completed_late']]
    return render(request, 'core/student_dashboard.html', context)

@login_required
@faculty_required
def faculty_dashboard(request):
    context, profile = _get_dashboard_context(request)
    
    from course.models import TaskAssignment
    assigned_tasks = TaskAssignment.objects.filter(created_by=request.user).order_by('-created_at')
    
    tasks_data = []
    for t in assigned_tasks:
        submissions = t.submissions.all()
        tasks_data.append({
            'task': t,
            'total_assigned': submissions.count(),
            'completed': submissions.filter(status__in=['completed', 'completed_late']).count(),
            'pending': submissions.filter(status='pending').count(),
            'in_progress': submissions.filter(status='in_progress').count(),
            'overdue': submissions.filter(status='overdue').count()
        })
    context['tasks_data'] = tasks_data
    
    from django.contrib.auth.models import User
    students = User.objects.filter(account_profile__role__iexact='student').order_by('username')
    context['available_students'] = students

    return render(request, 'core/faculty_dashboard.html', context)

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
    active_course = Course.objects.filter(user=request.user, is_active=True, is_deleted=False).first()
    if not active_course:
        # Fallback to session if is_active is not yet set
        course_id = request.session.get('active_course_id')
        if course_id:
            active_course = Course.objects.filter(user=request.user, id=course_id, is_deleted=False).first()
    
    if active_course:
        return JsonResponse({
            'status': 'success',
            'id': active_course.id,
            'title': active_course.title,
            'url': f"/course/{active_course.id}/"
        })
    return JsonResponse({'status': 'null'}, safe=False)

@login_required
@faculty_required
def create_task_assignment(request):
    from datetime import datetime
    
    if request.method == 'POST':
        try:
            from course.models import TaskAssignment, TaskSubmission, Course
            from django.contrib.auth.models import User
            
            title = request.POST.get('title')
            description = request.POST.get('description', '')
            task_type = request.POST.get('task_type')
            course_id = request.POST.get('course_id')
            priority = request.POST.get('priority', 'medium')
            assign_to = request.POST.get('assign_to') # 'entire_class', 'individual', 'selected'
            deadline_str = request.POST.get('deadline')
            
            deadline = None
            if deadline_str:
                from django.utils.dateparse import parse_datetime
                # Handle possible missing timezone by appending 'Z' or handling timezone aware. We'll use parse_datetime.
                deadline = parse_datetime(deadline_str)
                if deadline is None:
                    try:
                        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
                    except ValueError:
                        pass
            
            course = Course.objects.get(id=course_id)
            
            task = TaskAssignment.objects.create(
                title=title,
                description=description,
                task_type=task_type,
                course=course,
                created_by=request.user,
                deadline=deadline,
                priority=priority
            )
            
            students_to_assign = []
            if assign_to == 'entire_class':
                students_to_assign = list(User.objects.filter(account_profile__role__iexact='student'))
            else:
                s_ids = request.POST.getlist('student_ids')
                if s_ids:
                    students_to_assign = list(User.objects.filter(id__in=s_ids))
            
            submissions = []
            for student in students_to_assign:
                submissions.append(TaskSubmission(
                    assignment=task,
                    student=student,
                    status='pending'
                ))
            if submissions:
                TaskSubmission.objects.bulk_create(submissions)
            
            messages.success(request, f"Task '{title}' successfully assigned to {len(students_to_assign)} student(s).")
        except Exception as e:
            messages.error(request, f"Error creating task: {str(e)}")
            
    return redirect('core:faculty_dashboard')

@login_required
def start_task(request, submission_id):
    from course.models import TaskSubmission
    from django.utils import timezone
    from django.shortcuts import get_object_or_404
    submission = get_object_or_404(TaskSubmission, id=submission_id, student=request.user)
    
    if submission.status == 'pending':
        submission.status = 'in_progress'
        submission.started_at = timezone.now()
        submission.save()
    
    task = submission.assignment
    if task.task_type == 'quiz':
        return redirect('quiz:quiz_subjects') 
    elif task.task_type == 'topic':
        return redirect('ai_tutor:tutor_home') 
    elif task.task_type == 'flashcards':
        return redirect('flashcard_generator:flashcard_home')
    elif task.task_type == 'summary':
        return redirect('generator:study_plan')
    else:
        return redirect('core:student_dashboard')

@login_required
def complete_task(request, submission_id):
    from course.models import TaskSubmission
    from django.utils import timezone
    from django.shortcuts import get_object_or_404
    submission = get_object_or_404(TaskSubmission, id=submission_id, student=request.user)
    
    now = timezone.now()
    if submission.assignment.deadline and now > submission.assignment.deadline:
        submission.status = 'completed_late'
    else:
        submission.status = 'completed'
        
    submission.completed_at = now
    submission.save()
    
    from django.contrib import messages
    messages.success(request, f"Task '{submission.assignment.title}' marked as completed!")
    return redirect('core:student_dashboard')


