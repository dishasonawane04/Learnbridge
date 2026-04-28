from django.utils import timezone
from datetime import timedelta
from .models import ActivityLog
from django.db.models.functions import TruncDate
from django.db.models import Count

class ConsistencyEngine:
    @staticmethod
    def get_metrics_for_student(user):
        """
        Calculates streak and frequency metrics for a student.
        """
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        # 1. Get all distinct active dates for the user
        active_dates = ActivityLog.objects.filter(user=user)\
            .annotate(date=TruncDate('timestamp'))\
            .values_list('date', flat=True)\
            .order_by('-date').distinct()
        
        # Convert to a set for fast lookup and list for ordered processing
        date_set = set(active_dates)
        date_list = sorted(list(date_set), reverse=True)
        
        # 2. Calculate Streak
        streak = 0
        if date_list:
            current_check = today
            # If they haven't logged in today, their streak might have ended yesterday
            if date_list[0] != today:
                current_check = today - timedelta(days=1)
                
            # Now count backwards
            for active_date in date_list:
                if active_date == current_check:
                    streak += 1
                    current_check -= timedelta(days=1)
                elif active_date < current_check:
                    # Streak broken
                    break
        
        # 3. Calculate 7-day Frequency
        active_7d = [d for d in date_set if d > today - timedelta(days=7)]
        count_7d = len(active_7d)
        
        # 4. Determine Status and Insight
        status = "Moderate Consistency"
        icon = "⏳"
        color_class = "moderate" # We will define this in CSS
        insight = "Student activity is inconsistent and may need follow-up."
        
        if len(date_list) <= 1:
            status = "New Student"
            icon = "🌱"
            color_class = "new"
            insight = "Getting started on the platform."
        elif streak >= 5 and count_7d >= 4:
            status = "High Consistency"
            icon = "🔥"
            color_class = "high"
            insight = "Student is engaging regularly with the platform."
        elif streak <= 2 or count_7d < 3:
            status = "Irregular Student"
            icon = "⚠️"
            color_class = "irregular"
            insight = "Student has recently reduced engagement."
            
        return {
            'streak': streak,
            'active_7d': count_7d,
            'status_label': status,
            'status_icon': icon,
            'color_class': color_class,
            'insight': insight
        }


class AnalyticsEngine:
    @staticmethod
    def get_class_analytics():
        """
        Aggregates class-wide analytics, insights, and recommendations.
        """
        from quiz.models import QuizAttempt, StudentAnswer
        from accounts.models import UserProfile
        from collections import Counter
        from django.db.models import Avg

        now = timezone.now()
        profiles = UserProfile.objects.filter(role='Student').select_related('user')
        
        student_data = []
        for profile in profiles:
            attempts = QuizAttempt.objects.filter(user=profile.user)
            all_pcts = list(attempts.values_list('percentage', flat=True))
            quiz_avg = round(sum(all_pcts) / len(all_pcts), 1) if all_pcts else None
            
            student_data.append({
                'user': profile.user,
                'display_name': profile.full_name or profile.user.username,
                'quiz_avg': quiz_avg,
                'attempt_count': len(all_pcts),
                'last_active': ActivityLog.objects.filter(user=profile.user).order_by('-timestamp').values_list('timestamp', flat=True).first(),
            })

        scored_students = [s for s in student_data if s['quiz_avg'] is not None]
        avg_performance = round(sum(s['quiz_avg'] for s in scored_students) / len(scored_students), 1) if scored_students else None

        # Common weak topics
        all_wrong = StudentAnswer.objects.filter(is_correct=False).exclude(topic='').exclude(topic__isnull=True)
        topic_counter = Counter(ans.topic.strip() for ans in all_wrong if (ans.topic or '').strip())
        class_weak_topics = topic_counter.most_common(6)

        # Recommendations logic extracted from faculty_dashboard
        recommendations = []
        if avg_performance is not None and avg_performance < 50:
            recommendations.append({
                'priority': 'urgent',
                'title': 'Schedule a Practice Quiz',
                'desc': f'Class average is only {avg_performance}%. A structured practice quiz can help students identify gaps.',
            })
        
        if class_weak_topics:
            top_topic, top_count = class_weak_topics[0]
            recommendations.append({
                'priority': 'urgent' if top_count >= 5 else 'moderate',
                'title': f'Revision Class: {top_topic}',
                'desc': f'"{top_topic}" is the most common weak area ({top_count} mistakes). Focused revision is recommended.',
            })

        return {
            'student_data': student_data,
            'total_students': len(student_data),
            'avg_performance': avg_performance,
            'class_weak_topics': class_weak_topics,
            'recommendations': recommendations,
        }

    @staticmethod
    def get_individual_student_analytics(user):
        """
        Aggregates individual student analytics and insights.
        """
        from quiz.models import QuizAttempt, StudentAnswer
        
        attempts = QuizAttempt.objects.filter(user=user).order_by('-created_at')
        scores = list(attempts.values_list('percentage', flat=True))
        
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0
        high_score = round(max(scores), 1) if scores else 0
        latest_score = round(scores[0], 1) if scores else 0
        
        trend = "Consistent"
        if len(scores) >= 2:
            if scores[0] > scores[1] + 5: trend = "Improving"
            elif scores[0] < scores[1] - 5: trend = "Declining"
            
        topic_counts = {}
        for ans in StudentAnswer.objects.filter(attempt__user=user, is_correct=False):
            t = (ans.topic or '').strip()
            if t and t.lower() not in ('', 'general', 'mixed'):
                topic_counts[t] = topic_counts.get(t, 0) + 1
        weak_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        ai_insights = []
        if avg_score >= 75:
            ai_insights.append("Student shows strong academic grasp with high quiz accuracy.")
        elif avg_score >= 50:
            ai_insights.append("Average performance. Consistent practice will improve accuracy.")
        else:
            ai_insights.append("Student is struggling with core concepts.")

        return {
            'avg_score': avg_score,
            'high_score': high_score,
            'latest_score': latest_score,
            'trend': trend,
            'weak_topics': weak_topics,
            'ai_insights': ai_insights,
            'attempts_preview': attempts[:10],
        }
