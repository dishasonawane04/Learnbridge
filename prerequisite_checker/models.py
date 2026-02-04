from django.db import models
from django.conf import settings
from django.utils import timezone

class PrerequisiteSession(models.Model):
    """
    Stores the overall session for a prerequisite check.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prerequisite_sessions')
    unit = models.ForeignKey('course.CourseUnit', on_delete=models.SET_NULL, null=True, blank=True, related_name='prerequisite_sessions')
    target_topic = models.CharField(max_length=255)
    readiness_score = models.IntegerField(null=True, blank=True) # 0-100
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.target_topic}"

class ConceptResult(models.Model):
    """
    Stores the result for a single prerequisite concept within a session.
    """
    STATUS_CHOICES = [
        ('Strong', 'Strong'),
        ('Weak', 'Weak'),
        ('Missing', 'Missing'),
    ]

    session = models.ForeignKey(PrerequisiteSession, on_delete=models.CASCADE, related_name='concept_results')
    concept_name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    feedback = models.TextField(blank=True) # Specific AI feedback for this concept
    
    # Store the question asked and user's answer for review
    diagnostic_question = models.TextField(blank=True)
    user_answer = models.TextField(blank=True)

    def __str__(self):
        return f"{self.concept_name} ({self.status})"
