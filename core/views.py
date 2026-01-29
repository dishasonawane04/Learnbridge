from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import UserProfile, UserActivity
from django.db import models
from django.db.models import Avg, Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

def home(request):
    return render(request, 'core/home.html')

@login_required
def dashboard(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=request.user, role='student')
        profile = request.user.userprofile

    # 1. Analytics logic
    activities = UserActivity.objects.filter(user=request.user).order_by('-timestamp')
    
    # 2. Summary stats
    total_time = activities.aggregate(Sum('time_spent'))['time_spent__sum'] or 0
    completed_topics = activities.filter(outcome='completed').values('topic').distinct().count()
    avg_score = activities.filter(quiz_score__isnull=False).aggregate(Avg('quiz_score'))['quiz_score__avg'] or 0
    
    # 3. Streak Calculation
    streak = 0
    if activities.exists():
        activity_dates = activities.values_list('timestamp__date', flat=True).distinct()
        today = timezone.now().date()
        current_date = today
        
        # Check if they had activity today or yesterday to continue streak
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

    # 4. Topic Mastery & Accuracy (Advanced)
    # Calculate mastery as: (avg_score * 0.7) + (completion_count * 0.3) - capped at 100
    topic_stats = activities.values('topic').annotate(
        avg_topic_score=Avg('quiz_score'),
        attempts=Count('id'),
        success_count=Count('id', filter=Q(outcome='completed'))
    )
    
    mastery_data = []
    for stat in topic_stats:
        avg_score_val = stat['avg_topic_score'] or 0
        mastery = min(100, int((avg_score_val * 0.8) + (min(stat['success_count'], 5) * 4)))
        mastery_data.append({
            'topic': stat['topic'],
            'mastery': mastery,
            'accuracy': int(avg_score_val)
        })

    # 5. AI Recommendations
    recommendations = []
    needs_revision = activities.filter(outcome='needs_revision').values('topic').distinct()[:2]
    for activity in needs_revision:
        recommendations.append({
            'topic': activity['topic'],
            'reason': "You struggled with this topic in your last quiz. Let's master the basics.",
            'action': "Revise Now"
        })
    
    if len(recommendations) < 3:
        # Suggest something new or popular if not enough revision tasks
        recommendations.append({
            'topic': "Advanced Python Internals" if profile.role == 'student' else "Teaching Methodologies",
            'reason': "Based on your progress, you're ready for more complex concepts.",
            'action': "Explore New"
        })

    # 6. Recent Activity & Topic Dist
    recent_activity = activities[:10]
    topic_dist = list(activities.values('topic').annotate(count=Count('id')))

    context = {
        'profile': profile,
        'total_time': total_time // 60,
        'completed_topics': completed_topics,
        'avg_score': int(avg_score),
        'streak': streak,
        'mastery_data': mastery_data,
        'recommendations': recommendations,
        'recent_activity': recent_activity,
        'topic_dist': topic_dist,
    }
    
    if profile.role == 'teacher':
        return render(request, 'core/teacher_dashboard.html', context)
    return render(request, 'core/student_dashboard.html', context)

@login_required
def role_selection(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ['student', 'teacher']:
            UserProfile.objects.get_or_create(user=request.user, defaults={'role': role})
            return redirect('dashboard')
    return render(request, 'core/role_selection.html')
