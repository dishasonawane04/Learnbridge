from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from .models import ActivityLog, ScreenTimeLog
from django.http import JsonResponse
import json
from django.db.models import Max, F
from accounts.models import UserProfile
from django.contrib.auth.models import User
from accounts.decorators import faculty_required
from prerequisite_checker.models import PrerequisiteSession
from .services import ConsistencyEngine

@faculty_required
def faculty_consistency_view(request):
    """
    Overview of student engagement consistency.
    """
    students = UserProfile.objects.filter(role='Student')
    student_data = []

    for profile in students:
        user = profile.user
        metrics = ConsistencyEngine.get_metrics_for_student(user)
        
        student_data.append({
            'user': user,
            'full_name': profile.full_name,
            'metrics': metrics
        })

    return render(request, 'analytics/faculty_consistency.html', {
        'students': student_data,
        'total_students': len(student_data)
    })


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
    Overview of all students' activity — with overview stats, enriched
    per-student data for client-side search/filter.
    """
    from quiz.models import QuizAttempt
    from course.models import Course

    now = timezone.now()
    active_window = timedelta(days=7)
    moderate_window = timedelta(days=30)

    profiles = UserProfile.objects.filter(role='Student').select_related('user')

    # ── Build student data ──────────────────────────────────────────────
    student_data = []
    for profile in profiles:
        user = profile.user
        logs = ActivityLog.objects.filter(user=user).order_by('-timestamp')

        last_log = logs.first()
        last_active = last_log.timestamp if last_log else None

        # Determine activity status
        if last_active is None:
            activity_status = 'never'
        elif (now - last_active) <= active_window:
            activity_status = 'active'
        elif (now - last_active) <= moderate_window:
            activity_status = 'moderate'
        else:
            activity_status = 'inactive'

        # Real quiz average from QuizAttempt
        attempts = QuizAttempt.objects.filter(user=user)
        attempt_count = attempts.count()
        if attempt_count > 0:
            all_pcts = list(attempts.values_list('percentage', flat=True))
            quiz_avg = round(sum(all_pcts) / len(all_pcts), 1)
        else:
            quiz_avg = None  # no quiz data

        # Performance class
        if quiz_avg is None:
            perf_class = 'no_data'
        elif quiz_avg >= 75:
            perf_class = 'high'
        elif quiz_avg >= 40:
            perf_class = 'average'
        else:
            perf_class = 'low'

        # Status label (keep backward compat)
        if quiz_avg is not None and quiz_avg < 60:
            status = 'Needs Help'
        elif activity_status in ('inactive', 'never'):
            status = 'Inactive'
        else:
            status = 'On Track'

        # Courses this student has attempted quizzes in
        course_ids = list(
            attempts.exclude(course=None)
            .values_list('course_id', flat=True)
            .distinct()
        )

        # Display name with fallback chain
        display_name = (
            profile.full_name.strip()
            or f"{user.first_name} {user.last_name}".strip()
            or user.username
        )

        student_data.append({
            'user': user,
            'full_name': profile.full_name,
            'display_name': display_name,
            'email': user.email,
            'ai_interactions': logs.filter(app_name='ai_tutor').count(),
            'flashcards_generated': logs.filter(app_name='flashcard', activity_type='deck_generated').count(),
            'quiz_avg': quiz_avg if quiz_avg is not None else 0,
            'quiz_avg_raw': quiz_avg,          # None if no data
            'last_active': last_active,
            'status': status,
            'activity_status': activity_status,
            'perf_class': perf_class,
            'course_ids': course_ids,
            'attempt_count': attempt_count,
        })

    # ── Overview stats ──────────────────────────────────────────────────
    total_students = len(student_data)
    active_users = sum(1 for s in student_data if s['activity_status'] == 'active')

    scored_students = [s for s in student_data if s['quiz_avg_raw'] is not None]
    avg_performance = (
        round(sum(s['quiz_avg_raw'] for s in scored_students) / len(scored_students), 1)
        if scored_students else None
    )

    # ── Courses for filter dropdown ─────────────────────────────────────
    course_ids_all = set()
    for s in student_data:
        course_ids_all.update(s['course_ids'])
    courses_for_filter = Course.objects.filter(id__in=course_ids_all).values('id', 'title').order_by('title')

    # ── Class Insights ──────────────────────────────────────────────────
    from quiz.models import StudentAnswer
    from collections import Counter


    # Common weak topics across all students
    all_wrong = StudentAnswer.objects.filter(is_correct=False).exclude(topic='').exclude(topic__isnull=True)
    topic_counter = Counter(ans.topic.strip() for ans in all_wrong if (ans.topic or '').strip())
    class_weak_topics = [(t, c) for t, c in topic_counter.most_common(6) if t.lower() not in ('', 'general', 'mixed')]

    # Students needing attention (low score or inactive)
    needs_attention = [s for s in student_data if s['status'] in ('Needs Help', 'Inactive')][:5]

    # Top performers
    top_performers = sorted(
        [s for s in student_data if s['quiz_avg_raw'] is not None],
        key=lambda x: x['quiz_avg_raw'], reverse=True
    )[:3]

    # Class-level AI insight text
    if avg_performance is None:
        class_insight = "No quiz data available yet. Encourage students to attempt quizzes."
    elif avg_performance >= 75:
        class_insight = "Class is performing strongly overall. Consider introducing advanced challenges."
    elif avg_performance >= 50:
        class_insight = f"Class average is {avg_performance}%. Targeted topic revision can push scores higher."
    else:
        class_insight = f"Class is struggling with quizzes (avg {avg_performance}%). A structured revision session is recommended."

    if len(needs_attention) > total_students * 0.5:
        class_insight += " More than half the class needs attention."

    # ── Recommended Faculty Actions ─────────────────────────────────────
    recommendations = []

    # 1. Class avg below 50% → schedule practice quiz
    if avg_performance is not None and avg_performance < 50:
        recommendations.append({
            'priority': 'urgent',
            'icon': 'ph-warning-circle',
            'title': 'Schedule a Practice Quiz',
            'desc': f'Class average is only {avg_performance}%. A structured practice quiz can help students identify gaps.',
            'badge': f'{avg_performance}% avg',
        })
    elif avg_performance is not None and avg_performance < 65:
        recommendations.append({
            'priority': 'moderate',
            'icon': 'ph-clipboard-text',
            'title': 'Consider a Revision Session',
            'desc': f'Class average of {avg_performance}% is below target. A targeted revision session is recommended.',
            'badge': f'{avg_performance}% avg',
        })

    # 2. Common weak topic → suggest revision class on that topic
    if class_weak_topics:
        top_topic, top_count = class_weak_topics[0]
        recommendations.append({
            'priority': 'urgent' if top_count >= 5 else 'moderate',
            'icon': 'ph-book-open',
            'title': f'Revision Class: {top_topic}',
            'desc': f'"{top_topic}" is the most common weak area across the class ({top_count} mistakes). A focused revision session is recommended.',
            'badge': f'{top_count} mistakes',
        })

    # 3. Inactive students (inactive > 10 days) → suggest follow-up
    long_inactive = [
        s for s in student_data
        if s['last_active'] and (now - s['last_active']).days >= 10
    ]
    never_active = [s for s in student_data if s['last_active'] is None]
    if long_inactive:
        names = ', '.join(s['display_name'] for s in long_inactive[:3])
        extra = f' and {len(long_inactive) - 3} more' if len(long_inactive) > 3 else ''
        recommendations.append({
            'priority': 'urgent',
            'icon': 'ph-user-minus',
            'title': 'Follow Up with Inactive Students',
            'desc': f'{len(long_inactive)} student(s) inactive for 10+ days: {names}{extra}. Engagement follow-up recommended.',
            'badge': f'{len(long_inactive)} inactive',
        })
    if never_active:
        recommendations.append({
            'priority': 'moderate',
            'icon': 'ph-ghost',
            'title': 'Onboard Uninitiated Students',
            'desc': f'{len(never_active)} student(s) have never used the platform. Encourage them to log in and start a course.',
            'badge': f'{len(never_active)} never active',
        })

    # 4. Strong performers → suggest advanced challenge
    if top_performers:
        names = ', '.join(s['display_name'] for s in top_performers[:2])
        scores = ', '.join(f"{s['quiz_avg_raw']:.1f}%" for s in top_performers[:2])
        recommendations.append({
            'priority': 'positive',
            'icon': 'ph-rocket-launch',
            'title': 'Assign Advanced Challenge Quiz',
            'desc': f'Top performers ({names}) are scoring {scores}. Challenge them with advanced-level material to maintain momentum.',
            'badge': 'Top performers',
        })

    # 5. More than half the class needs attention
    if total_students > 0 and len(needs_attention) / total_students > 0.5:
        recommendations.append({
            'priority': 'urgent',
            'icon': 'ph-siren',
            'title': 'Class-Wide Intervention Needed',
            'desc': f'Over 50% of students ({len(needs_attention)}/{total_students}) are flagged as Inactive or Needs Help. Consider a structured re-engagement plan.',
            'badge': f'{len(needs_attention)} students',
        })

    # 6. No quiz data at all → encourage quizzes
    if avg_performance is None:
        recommendations.append({
            'priority': 'info',
            'icon': 'ph-question',
            'title': 'Encourage Students to Take Quizzes',
            'desc': 'No quiz attempts recorded yet. Share quiz links with students to start tracking performance.',
            'badge': 'No data',
        })

    context = {

        'students': student_data,
        'total_students': total_students,
        'active_users': active_users,
        'avg_performance': avg_performance,
        'courses_for_filter': list(courses_for_filter),
        # Class Insights
        'class_weak_topics': class_weak_topics,
        'needs_attention': needs_attention,
        'top_performers': top_performers,
        'class_insight': class_insight,
        # Recommended Actions
        'recommendations': recommendations,
    }
    return render(request, 'analytics/faculty_dashboard.html', context)



@faculty_required
def faculty_student_detail(request, user_id):
    """
    Rich insight profile for a single student — faculty view.
    Covers: performance trend, screen time, quiz history, weak topics, AI insights.
    """
    from quiz.models import QuizAttempt, StudentAnswer

    target_user = get_object_or_404(User, id=user_id)
    profile = UserProfile.objects.filter(user=target_user).first()
    now = timezone.now()

    display_name = (
        (profile.full_name.strip() if profile and profile.full_name else '')
        or f"{target_user.first_name} {target_user.last_name}".strip()
        or target_user.username
    )

    # ── Activity logs ───────────────────────────────────────────────────
    logs = ActivityLog.objects.filter(user=target_user).order_by('-timestamp')
    last_active = logs.first().timestamp if logs.exists() else None

    ai_interactions = logs.filter(app_name='ai_tutor').count()
    flashcards_count = logs.filter(app_name='flashcard', activity_type='deck_generated').count()

    # ── Screen Time ─────────────────────────────────────────────────────
    screen_logs = ScreenTimeLog.objects.filter(user=target_user)
    total_seconds = screen_logs.aggregate(t=Sum('duration_seconds'))['t'] or 0
    total_minutes = total_seconds // 60

    # Per-tool breakdown
    tool_time = {}
    for tl in screen_logs.values('tool_name').annotate(secs=Sum('duration_seconds')):
        tool_time[tl['tool_name']] = tl['secs'] // 60  # minutes

    # Most active hour
    hour_counts = {}
    for tl in screen_logs:
        h = tl.started_at.hour
        hour_counts[h] = hour_counts.get(h, 0) + tl.duration_seconds
    if hour_counts:
        peak_hour = max(hour_counts, key=hour_counts.get)
        if 5 <= peak_hour < 12:
            peak_label = f"{peak_hour}:00 (Morning)"
        elif 12 <= peak_hour < 17:
            peak_label = f"{peak_hour}:00 (Afternoon)"
        elif 17 <= peak_hour < 21:
            peak_label = f"{peak_hour}:00 (Evening)"
        else:
            peak_label = f"{peak_hour}:00 (Night)"
    else:
        peak_label = "No data"

    # Daily average (over last 30 days)
    days_tracked = min(screen_logs.dates('started_at', 'day').count(), 30) or 1
    daily_avg_min = total_minutes // days_tracked

    # Screen time insight
    dominant_tool = max(tool_time, key=tool_time.get) if tool_time else None
    if dominant_tool == 'ai_tutor':
        screen_insight = "High AI Tutor usage — student shows curiosity and learning intent."
    elif dominant_tool == 'flashcard':
        screen_insight = "Student prefers revision-based learning via flashcards."
    elif dominant_tool == 'quiz':
        screen_insight = "Student is practice-oriented with frequent quiz usage."
    else:
        screen_insight = "Study time data available. Encourage consistent daily sessions."

    if total_minutes < 30:
        screen_insight = "Very low platform usage — student may need engagement follow-up."

    # ── Quiz performance ─────────────────────────────────────────────────
    attempts = QuizAttempt.objects.filter(user=target_user).order_by('-created_at')
    attempt_count = attempts.count()

    scores = list(attempts.values_list('percentage', flat=True))
    if scores:
        avg_score = round(sum(scores) / len(scores), 1)
        high_score = round(max(scores), 1)
        latest_score = round(scores[0], 1)

        # Trend: compare last 3 vs next 3
        if len(scores) >= 4:
            recent = sum(scores[:3]) / 3
            older = sum(scores[3:min(6, len(scores))]) / len(scores[3:min(6, len(scores))])
            if recent > older + 5:
                trend = 'Improving'
                trend_icon = 'trend-up'
                perf_insight = "Student is improving steadily across recent quizzes."
            elif recent < older - 5:
                trend = 'Declining'
                trend_icon = 'trend-down'
                perf_insight = "Performance dropping recently. Needs targeted revision."
            else:
                trend = 'Consistent'
                trend_icon = 'equals'
                perf_insight = "Consistent performer. Encourage stretch challenges."
        elif avg_score >= 75:
            trend, trend_icon = 'Strong', 'star'
            perf_insight = "Consistently high scores — strong understanding of topics."
        elif avg_score < 50:
            trend, trend_icon = 'Needs Improvement', 'warning'
            perf_insight = "Struggles with quizzes. In-depth topic revision recommended."
        else:
            trend, trend_icon = 'Average', 'equals'
            perf_insight = "Average performance. Targeted practice can push scores higher."
    else:
        avg_score = high_score = latest_score = None
        trend, trend_icon = 'No Data', 'minus'
        perf_insight = "No quiz attempts recorded. Encourage student to take quizzes."

    # ── Quiz history rows ────────────────────────────────────────────────
    quiz_rows = []
    for a in attempts[:15]:
        wrong = (a.total or 0) - a.score
        pct = a.percentage
        if pct >= 75:
            chip = 'high'
        elif pct >= 40:
            chip = 'avg'
        else:
            chip = 'low'
        quiz_rows.append({
            'attempt': a,
            'wrong': wrong,
            'chip': chip,
        })

    # Quiz history insight
    if attempt_count >= 3 and scores:
        recent3 = scores[:3]
        if all(s >= 70 for s in recent3):
            quiz_hist_insight = "Last 3 quiz scores are strong — student is well-prepared."
        elif all(s < 50 for s in recent3):
            quiz_hist_insight = "Attempts frequent but accuracy consistently low. Concept gaps likely."
        else:
            quiz_hist_insight = f"Mixed recent results. Latest score: {latest_score}%."
    elif attempt_count > 0:
        quiz_hist_insight = f"Only {attempt_count} attempt(s) so far. More practice encouraged."
    else:
        quiz_hist_insight = "No quiz attempts yet."

    # ── Weak topics from StudentAnswer ───────────────────────────────────
    wrong_answers = StudentAnswer.objects.filter(
        attempt__user=target_user, is_correct=False
    )

    topic_counts = {}
    for ans in wrong_answers:
        t = (ans.topic or '').strip()
        if t and t.lower() not in ('', 'general', 'mixed'):
            topic_counts[t] = topic_counts.get(t, 0) + 1

    # Also pull from ActivityLog (legacy)
    log_topics = logs.exclude(topic__isnull=True).exclude(topic='')
    for log in log_topics.filter(score__lt=60):
        t = log.topic.strip()
        if t:
            topic_counts[t] = topic_counts.get(t, 0) + 1

    weak_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:6]

    if weak_topics:
        top_weak = weak_topics[0][0]
        weak_insight = f"Repeated mistakes detected in \"{top_weak}\". Targeted revision recommended."
    else:
        weak_insight = "No specific weak topics identified yet. Topic tags will appear after quiz attempts."

    # ── AI Insight summary ───────────────────────────────────────────────
    ai_insights = []

    # Activity level
    if last_active is None:
        ai_insights.append(("warning", "Student has never logged in. Immediate follow-up recommended."))
    elif (now - last_active).days > 14:
        ai_insights.append(("warning", "Student engagement dropped recently and may need follow-up."))
    elif (now - last_active).days <= 2:
        ai_insights.append(("positive", "Student is actively using the platform. Good engagement."))

    # Performance
    if avg_score is not None:
        if avg_score >= 75:
            ai_insights.append(("positive", f"High average score ({avg_score}%) — strong academic grasp."))
        elif avg_score >= 50:
            ai_insights.append(("neutral", f"Average performance ({avg_score}%). Consistent practice will help."))
        else:
            ai_insights.append(("warning", f"Low average score ({avg_score}%). Class is struggling — targeted revision needed."))
    else:
        ai_insights.append(("neutral", "No quiz data available. Encourage quiz attempts to track performance."))

    # Tool usage
    if ai_interactions > 10:
        ai_insights.append(("positive", "High AI Tutor usage indicates curiosity and self-directed learning."))
    if flashcards_count > 5:
        ai_insights.append(("positive", "Regular flashcard use shows consistent revision habits."))

    # Weak topics
    if len(weak_topics) >= 3:
        ai_insights.append(("warning", f"Multiple weak topics detected. Concept-wise revision plan recommended."))

    # Trend
    if trend == 'Improving':
        ai_insights.append(("positive", "Performance improving over time — current study habits are working."))
    elif trend == 'Declining':
        ai_insights.append(("warning", "Recent scores are declining despite attempts. Quality of study needs attention."))

    # Default fallback
    if not ai_insights:
        ai_insights.append(("neutral", "Insufficient data for full insight. More activity will improve predictions."))

    context = {
        'target_user': target_user,
        'profile': profile,
        'display_name': display_name,
        'last_active': last_active,
        # Performance
        'avg_score': avg_score,
        'high_score': high_score,
        'latest_score': latest_score,
        'attempt_count': attempt_count,
        'trend': trend,
        'trend_icon': trend_icon,
        'perf_insight': perf_insight,
        # Screen time
        'total_minutes': total_minutes,
        'daily_avg_min': daily_avg_min,
        'peak_label': peak_label,
        'tool_time': tool_time,
        'screen_insight': screen_insight,
        'ai_interactions': ai_interactions,
        'flashcards_count': flashcards_count,
        # Quiz history
        'quiz_rows': quiz_rows,
        'quiz_hist_insight': quiz_hist_insight,
        # Weak topics
        'weak_topics': weak_topics,
        'weak_insight': weak_insight,
        # AI insights
        'ai_insights': ai_insights,
    }
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

@faculty_required
def faculty_student_performance(request):
    """
    Detailed performance overview for all students (Weak Topics, Strong Topics, etc).
    """
    students = UserProfile.objects.filter(role='Student')
    
    student_data = []
    for profile in students:
        user = profile.user
        logs = ActivityLog.objects.filter(user=user)
        
        # 1. Overall Score
        quiz_avg = logs.filter(app_name='flashcard', activity_type='quiz_completed').aggregate(score__avg=Avg('score'))['score__avg'] or 0
        overall_score = round(quiz_avg, 1)

        # 2. Weak & Strong Topics
        topic_logs = logs.exclude(topic__isnull=True).exclude(topic='')
        
        weak_topics = list(topic_logs.filter(outcome='needs_revision').values_list('topic', flat=True).distinct()[:3])
        if not weak_topics:
            weak_topics = list(topic_logs.filter(score__lt=60).values_list('topic', flat=True).distinct()[:3])
            
        strong_topics = list(topic_logs.filter(outcome='completed', score__gte=80).values_list('topic', flat=True).distinct()[:3])
        if not strong_topics:
            strong_topics = list(topic_logs.filter(score__gte=75).values_list('topic', flat=True).distinct()[:3])
        
        # 3. Improvement Trend
        quiz_logs = logs.filter(app_name='flashcard', activity_type='quiz_completed').order_by('-timestamp')
        trend = "Stable"
        if quiz_logs.count() >= 2:
            recent_avg = quiz_logs[:2].aggregate(s=Avg('score'))['s'] or 0
            older_avg = quiz_logs[2:].aggregate(s=Avg('score'))['s'] or recent_avg
            if recent_avg > older_avg + 5:
                trend = "Improving"
            elif recent_avg < older_avg - 5:
                trend = "Needs Attention"
        elif quiz_avg < 60 and quiz_logs.exists():
            trend = "Needs Attention"
            
        student_data.append({
            'user': user,
            'full_name': profile.full_name,
            'overall_score': overall_score,
            'weak_topics': weak_topics,
            'strong_topics': strong_topics,
            'trend': trend,
            'last_active': logs.first().timestamp if logs.exists() else None
        })
        
    return render(request, 'analytics/faculty_student_performance.html', {'students': student_data})

@faculty_required
def faculty_screen_time_view(request):
    """
    Detailed screen time analytics for all students.
    """
    students = UserProfile.objects.filter(role='Student')
    student_data = []

    for profile in students:
        user = profile.user
        logs = ScreenTimeLog.objects.filter(user=user)
        
        # 1. Total Time
        total_seconds = logs.aggregate(total=Sum('duration_seconds'))['total'] or 0
        total_minutes = round(total_seconds / 60, 1)

        # 2. Most Used Tool
        tool_counts = logs.values('tool_name').annotate(total_time=Sum('duration_seconds')).order_by('-total_time')
        most_used = tool_counts.first()['tool_name'] if tool_counts.exists() else "None"
        least_used = tool_counts.last()['tool_name'] if tool_counts.exists() else "None"

        # 3. Course Breakdown
        course_stats_raw = logs.values('course__title').annotate(total_time=Sum('duration_seconds')).order_by('-total_time')
        course_stats = []
        for cs in course_stats_raw:
            course_stats.append({
                'title': cs['course__title'] or "General",
                'minutes': round(cs['total_time'] / 60, 1)
            })
        
        # 4. Generate Insights
        insight = "No data yet."
        if total_seconds > 0:
            if most_used == 'flashcard' and tool_counts.filter(tool_name='quiz').exists() and tool_counts.get(tool_name='quiz')['total_time'] < tool_counts.get(tool_name='flashcard')['total_time'] * 0.5:
                insight = "Student prefers revision (Flashcards) over assessment (Quizzes)."
            elif most_used == 'ai_tutor':
                insight = "High engagement with AI Tutor for concept clarification."
            elif total_seconds < 600: # Less than 10 mins
                insight = "Engagement is currently low. Needs attention."
            else:
                insight = "Balanced usage across various learning tools."

        student_data.append({
            'user': user,
            'full_name': profile.full_name,
            'total_minutes': total_minutes,
            'most_used': most_used.replace('_', ' ').title(),
            'least_used': least_used.replace('_', ' ').title(),
            'insight': insight,
            'course_breakdown': course_stats
        })

    return render(request, 'analytics/faculty_screen_time.html', {
        'students': student_data,
        'total_students': len(student_data)
    })

@login_required
def track_screen_time_api(request):
    """
    Lightweight API to track user presence in specific tools.
    Expects POST with: tool_name, course_id (optional), session_id (optional)
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tool_name = data.get('tool_name')
            course_id = data.get('course_id')
            duration = data.get('duration', 30) # Default to 30 second heartbeat if not specified

            if not tool_name:
                return JsonResponse({'status': 'error', 'message': 'Missing tool_name'}, status=400)

            # Log the screen time
            # For simplicity, we just create a new record for every heartbeat or update existing if very recent
            # Check for a "current" session (last 2 mins) to avoid fragmentation
            recent_log = ScreenTimeLog.objects.filter(
                user=request.user, 
                tool_name=tool_name,
                started_at__gte=timezone.now() - timedelta(minutes=2)
            ).first()

            if recent_log:
                recent_log.duration_seconds += duration
                recent_log.ended_at = timezone.now()
                recent_log.save()
            else:
                ScreenTimeLog.objects.create(
                    user=request.user,
                    tool_name=tool_name,
                    course_id=course_id,
                    duration_seconds=duration,
                    ended_at=timezone.now()
                )

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


# ── Quiz History + Analysis ────────────────────────────────────────────────

@faculty_required
def faculty_quiz_history(request, user_id):
    """
    Faculty view: full quiz attempt history and common mistake analysis for a student.
    """
    from quiz.models import QuizAttempt, StudentAnswer

    target_user = get_object_or_404(User, id=user_id)
    profile = UserProfile.objects.filter(user=target_user).first()
    full_name = profile.full_name if profile else target_user.username

    attempts = QuizAttempt.objects.filter(user=target_user).order_by('-created_at')

    # ── Summary stats ──────────────────────────────────────────────────────
    total_attempts = attempts.count()
    if total_attempts == 0:
        avg_score = high_score = low_score = 0
        trend = 'No Data'
    else:
        scores = list(attempts.values_list('percentage', flat=True))
        avg_score = round(sum(scores) / len(scores), 1)
        high_score = round(max(scores), 1)
        low_score = round(min(scores), 1)

        # Trend: compare most recent 3 vs previous 3
        if total_attempts >= 4:
            recent_avg = sum(scores[:3]) / 3
            older_avg = sum(scores[3:min(6, total_attempts)]) / len(scores[3:min(6, total_attempts)])
            if recent_avg > older_avg + 5:
                trend = 'Improving'
            elif recent_avg < older_avg - 5:
                trend = 'Needs Attention'
            else:
                trend = 'Stable'
        elif avg_score >= 75:
            trend = 'Stable'
        elif avg_score < 50:
            trend = 'Needs Attention'
        else:
            trend = 'Stable'

    # ── Per-attempt row data ───────────────────────────────────────────────
    attempt_rows = []
    for attempt in attempts:
        total_q = attempt.total or 1
        correct = attempt.score
        wrong = total_q - correct
        pct = attempt.percentage

        if pct >= 80:
            score_class = 'high'
        elif pct >= 50:
            score_class = 'medium'
        else:
            score_class = 'low'

        attempt_rows.append({
            'attempt': attempt,
            'correct': correct,
            'wrong': wrong,
            'score_class': score_class,
        })

    # ── Common mistakes: aggregate wrong answers by topic ──────────────────
    wrong_answers = StudentAnswer.objects.filter(
        attempt__user=target_user,
        is_correct=False
    )

    topic_counts = {}
    topic_type_counts = {}  # question_type → count
    difficulty_counts = {}

    for ans in wrong_answers:
        t = ans.topic.strip() if ans.topic.strip() else 'General'
        topic_counts[t] = topic_counts.get(t, 0) + 1

        qt = ans.question_type.strip() if ans.question_type.strip() else 'MCQ'
        topic_type_counts[qt] = topic_type_counts.get(qt, 0) + 1

        d = ans.difficulty.strip() if ans.difficulty.strip() else 'Unknown'
        difficulty_counts[d] = difficulty_counts.get(d, 0) + 1

    # Sort by worst
    topic_mistakes = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    type_mistakes = sorted(topic_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    total_wrong = wrong_answers.count()
    total_answered = StudentAnswer.objects.filter(attempt__user=target_user).count()
    overall_accuracy = round(((total_answered - total_wrong) / total_answered * 100), 1) if total_answered else 0

    # ── Faculty insight text ───────────────────────────────────────────────
    insight_lines = []
    if trend == 'Improving':
        insight_lines.append('Student is improving across recent quizzes.')
    elif trend == 'Needs Attention':
        insight_lines.append('Student performance is declining. Needs attention.')
    else:
        insight_lines.append('Student performance is stable.')

    if topic_mistakes:
        top_topic = topic_mistakes[0][0]
        if top_topic != 'General':
            insight_lines.append(f'Repeated mistakes detected in "{top_topic}" concepts.')

    if type_mistakes:
        top_type = type_mistakes[0][0]
        if top_type not in ('MCQ', 'Unknown'):
            insight_lines.append(f'Student struggles most with {top_type} questions.')

    if overall_accuracy < 60 and total_answered > 0:
        insight_lines.append('Overall accuracy is low. Targeted practice recommended.')

    context = {
        'target_user': target_user,
        'full_name': full_name,
        'total_attempts': total_attempts,
        'avg_score': avg_score,
        'high_score': high_score,
        'low_score': low_score,
        'trend': trend,
        'attempt_rows': attempt_rows,
        'topic_mistakes': topic_mistakes,
        'type_mistakes': type_mistakes,
        'overall_accuracy': overall_accuracy,
        'total_wrong': total_wrong,
        'insight_lines': insight_lines,
    }
    return render(request, 'analytics/faculty_quiz_history.html', context)


@faculty_required
def faculty_quiz_attempt_detail(request, attempt_id):
    """
    Faculty view: question-level review for a single quiz attempt.
    """
    from quiz.models import QuizAttempt, StudentAnswer

    attempt = get_object_or_404(QuizAttempt, id=attempt_id)
    answers = attempt.answers.all().order_by('id')

    profile = UserProfile.objects.filter(user=attempt.user).first()
    full_name = profile.full_name if profile else (attempt.user.username if attempt.user else 'Unknown')

    context = {
        'attempt': attempt,
        'answers': answers,
        'full_name': full_name,
        'correct_count': answers.filter(is_correct=True).count(),
        'wrong_count': answers.filter(is_correct=False).count(),
    }
    return render(request, 'analytics/quiz_attempt_detail.html', context)

