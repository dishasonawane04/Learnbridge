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
