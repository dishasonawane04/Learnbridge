from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from .models import ActivityLog
from accounts.models import UserProfile
from django.contrib.auth.models import User
from accounts.decorators import faculty_required
from prerequisite_checker.models import PrerequisiteSession

@login_required
def student_dashboard(request):
    """
    Displays the student's progress dashboard.
    """
    # 1. Date filters
    today = timezone.now()
    last_7_days = today - timedelta(days=7)
    
    # 2. Fetch logs
    logs = ActivityLog.objects.filter(user=request.user)
    
    # 3. Aggregate Key Metrics
    
    # AI Tutor Stats
    ai_questions = logs.filter(app_name='ai_tutor', activity_type='question_asked').count()
    
    # Flashcard Stats
    deck_gen = logs.filter(app_name='flashcard', activity_type='deck_generated').count()
    cards_reviewed = logs.filter(app_name='flashcard', activity_type='card_reviewed').count()
    quizzes_taken = logs.filter(app_name='flashcard', activity_type='quiz_completed').count()
    if quizzes_taken > 0:
        # Django avg returns a dict
        from django.db.models import Avg
        avg_score_dict = logs.filter(app_name='flashcard', activity_type='quiz_completed').aggregate(Avg('score'))
        avg_quiz_score = avg_score_dict['score__avg']
    else:
        avg_quiz_score = 0
        
    # Learning Streak (Simple implementation: Count distinct days in last 30 days)
    # A real streak needs contiguous days check, but distinct active days is a good proxy for "Consistency"
    active_days = logs.dates('timestamp', 'day').count()
    
    # Recent Activity (Last 5)
    recent_activity = logs.order_by('-timestamp')[:5]
    
    # Chart Data: Activity over last 7 days
    # Format: [Sun, Mon, Tue...]
    daily_counts = {}
    for i in range(7):
        day = (last_7_days + timedelta(days=i+1)).date()
        daily_counts[day.strftime('%Y-%m-%d')] = 0
        
    recent_logs = logs.filter(timestamp__gte=last_7_days)
    for log in recent_logs:
        day_str = log.timestamp.date().strftime('%Y-%m-%d')
        if day_str in daily_counts:
            daily_counts[day_str] += 1
            
    chart_labels = list(daily_counts.keys())
    chart_data = list(daily_counts.values())

    context = {
        'ai_questions': ai_questions,
        'deck_gen': deck_gen,
        'cards_reviewed': cards_reviewed,
        'quizzes_taken': quizzes_taken,
        'avg_quiz_score': round(avg_quiz_score or 0, 1),
        'active_days': active_days,
        'recent_activity': recent_activity,
        'chart_labels': chart_labels,
        'chart_data': chart_data
    }
    
    
    return render(request, 'analytics/student_dashboard.html', context)

@faculty_required
def faculty_dashboard(request):
    """
    Overview of all students' activity.
    """
    students = UserProfile.objects.filter(role='Student')
    
    student_data = []
    for profile in students:
        user = profile.user
        logs = ActivityLog.objects.filter(user=user)
        
        # Gather summary stats
        last_active = logs.first().timestamp if logs.exists() else None
        quiz_avg = logs.filter(app_name='flashcard', activity_type='quiz_completed').aggregate(score__avg=Avg('score'))['score__avg'] or 0
        
        # Determine status
        status = 'On Track'
        if quiz_avg < 60 and logs.filter(app_name='flashcard', activity_type='quiz_completed').exists():
             status = 'Needs Help'
        elif not last_active or (timezone.now() - last_active).days > 7:
             status = 'Inactive'
        
        student_data.append({
            'user': user,
            'full_name': profile.full_name,
            'ai_interactions': logs.filter(app_name='ai_tutor').count(),
            'flashcards_generated': logs.filter(app_name='flashcard', activity_type='deck_generated').count(),
            'quiz_avg': quiz_avg,
            'last_active': last_active,
            'status': status
        })
        
    return render(request, 'analytics/faculty_dashboard.html', {'students': student_data})

@faculty_required
def faculty_student_detail(request, user_id):
    """
    Detailed view of a single student for the teacher.
    """
    target_user = get_object_or_404(User, id=user_id)
    # We can reuse the student_dashboard logic but for a specific user
    # However, for simplicity and modularity, let's just copy the context generation or refactor.
    # Refactoring is better practice.
    
    context = get_student_stats(target_user)
    context['target_user'] = target_user # Pass the user object for the header
    
    return render(request, 'analytics/student_detail.html', context)

def get_student_stats(user):
    """Helper to generate stats context for a user."""
    today = timezone.now()
    last_7_days = today - timedelta(days=7)
    logs = ActivityLog.objects.filter(user=user)
    
    ai_questions = logs.filter(app_name='ai_tutor', activity_type='question_asked').count()
    deck_gen = logs.filter(app_name='flashcard', activity_type='deck_generated').count()
    cards_reviewed = logs.filter(app_name='flashcard', activity_type='card_reviewed').count()
    quizzes_taken = logs.filter(app_name='flashcard', activity_type='quiz_completed').count()
    
    if quizzes_taken > 0:
        from django.db.models import Avg
        avg_quiz_score = logs.filter(app_name='flashcard', activity_type='quiz_completed').aggregate(Avg('score'))['score__avg']
    else:
        avg_quiz_score = 0
        
    active_days = logs.dates('timestamp', 'day').count()
    recent_activity = logs.order_by('-timestamp')[:10] # Show more for teacher
    
    daily_counts = {}
    for i in range(7):
        day = (last_7_days + timedelta(days=i+1)).date()
        daily_counts[day.strftime('%Y-%m-%d')] = 0
        
    recent_logs = logs.filter(timestamp__gte=last_7_days)
    for log in recent_logs:
        day_str = log.timestamp.date().strftime('%Y-%m-%d')
        if day_str in daily_counts:
            daily_counts[day_str] += 1
            
    chart_labels = list(daily_counts.keys())
    chart_data = list(daily_counts.values())
    
    # Prerequisite Stats
    prereq_sessions = PrerequisiteSession.objects.filter(user=user).order_by('-created_at')

    return {
        'ai_questions': ai_questions,
        'deck_gen': deck_gen,
        'cards_reviewed': cards_reviewed,
        'quizzes_taken': quizzes_taken,
        'avg_quiz_score': round(avg_quiz_score or 0, 1),
        'active_days': active_days,
        'recent_activity': recent_activity,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'prereq_sessions': prereq_sessions
    }
