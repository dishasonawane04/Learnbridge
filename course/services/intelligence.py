from datetime import date, timedelta
from django.db.models import Avg, Sum, Count
from ..models import Course, CourseUnit, UserUnitCompletion, ConceptNode, UserConceptMastery, UserCourseReadiness, StudyActivity, AIStudyInsight

class AIInsightService:
    @staticmethod
    def calculate_course_readiness(user, course):
        """Calculates 0-100 readiness based on mastery and consistency"""
        concepts = ConceptNode.objects.filter(unit__course=course)
        if not concepts.exists():
            return 0.0
            
        mastery_avg = UserConceptMastery.objects.filter(
            user=user, concept__in=concepts
        ).aggregate(Avg('score'))['score__avg'] or 0.0
        
        # Consistency factor based on study activity in the last 7 days
        last_7_days = date.today() - timedelta(days=7)
        activity_days = StudyActivity.objects.filter(
            user=user, course=course, date__gte=last_7_days
        ).values('date').distinct().count()
        
        consistency_score = (activity_days / 7) * 100
        
        readiness, created = UserCourseReadiness.objects.get_or_create(
            user=user, course=course
        )
        # Formula: 80% mastery + 20% consistency
        readiness.readiness_percentage = (mastery_avg * 0.8) + (consistency_score * 0.2)
        readiness.consistency_score = consistency_score
        readiness.save()
        
        return readiness

    @staticmethod
    def estimate_completion_time(course):
        """Dynamic calculation based on units and concepts"""
        # Base: 1 hour per unit + 15 mins per concept
        units_count = course.units.count()
        concepts_count = ConceptNode.objects.filter(unit__course=course).count()
        
        total_minutes = (units_count * 60) + (concepts_count * 15)
        hours = total_minutes // 60
        mins = total_minutes % 60
        
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    @staticmethod
    def track_activity(user, course, activity_type, points=10):
        """Logs daily activity and updates engagement points"""
        activity, created = StudyActivity.objects.get_or_create(
            user=user, course=course, date=date.today(),
            defaults={'activity_type': activity_type, 'engagement_points': points}
        )
        if not created:
            activity.engagement_points += points
            activity.save()

    @staticmethod
    def get_heatmap_data(user, course):
        """Returns intensity data for the last 28 days (4 weeks)"""
        today = date.today()
        activity_map = {
            a['date']: a['engagement_points'] 
            for a in StudyActivity.objects.filter(
                user=user, course=course, 
                date__gte=today - timedelta(days=28)
            ).values('date', 'engagement_points')
        }
        
        heatmap = []
        for i in range(27, -1, -1):
            day = today - timedelta(days=i)
            points = activity_map.get(day, 0)
            # Intensity levels 0-4
            intensity = 0
            if points >= 50: intensity = 4
            elif points >= 30: intensity = 3
            elif points >= 15: intensity = 2
            elif points > 0: intensity = 1
            heatmap.append({'date': day, 'intensity': intensity, 'points': points})
            
        return heatmap

    @staticmethod
    def get_unit_insights(user, unit):
        """Aggregates mastery and weak points for a unit"""
        concepts = unit.concepts.all()
        if not concepts.exists():
            return {'mastery': 0, 'weak_concepts': []}
        
        mastery_avg = UserConceptMastery.objects.filter(
            user=user, concept__in=concepts
        ).aggregate(Avg('score'))['score__avg'] or 0
        
        weak_concepts = ConceptNode.objects.filter(
            unit=unit,
            userconceptmastery__user=user,
            userconceptmastery__score__lt=60
        )
        
        return {
            'mastery': int(mastery_avg),
            'weak_concepts': weak_concepts
        }

    @staticmethod
    def generate_daily_insight(user, course):
        """Generates a contextual study tip if none exists for today"""
        today_insight = AIStudyInsight.objects.filter(
            user=user, course=course, created_at__date=date.today()
        ).first()
        
        if today_insight:
            return today_insight
            
        # Logic to generate insight based on weak spots
        readiness = UserCourseReadiness.objects.filter(user=user, course=course).first()
        
        if readiness and readiness.readiness_percentage < 40:
            content = "Fundamentals build mastery. Revisit the earliest units to strengthen your foundation."
            insight_type = 'warning'
        elif readiness and readiness.readiness_percentage > 80:
            content = "You're approaching peak readiness! Try the 'Expert' explanations to challenge yourself."
            insight_type = 'motivation'
        else:
            content = "Keep the momentum! A quick 15-minute quiz today will boost your retention."
            insight_type = 'tip'
            
        return AIStudyInsight.objects.create(
            user=user, course=course, content=content, insight_type=insight_type
        )
