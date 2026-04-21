from django.db import models
from django.conf import settings
from django.utils import timezone

class ActivityLog(models.Model):
    """
    Logs student activity across different apps for analytics.
    """
    APP_CHOICES = [
        ('ai_tutor', 'AI Tutor'),
        ('learning_support', 'Learning Support'),
        ('flashcard', 'Flashcard Generator'),
        ('lor', 'LOR Generator'),
        ('course', 'Course Management'),
        ('system', 'System Content'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity_logs')
    course = models.ForeignKey('course.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    app_name = models.CharField(max_length=50, choices=APP_CHOICES)
    activity_type = models.CharField(max_length=100) # e.g., 'question_asked', 'quiz_completed'
    topic = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Store extra details flexibility (e.g., score, hints_used, card_count)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Common metrics extracted for easier aggregation
    score = models.IntegerField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    input_type = models.CharField(max_length=20, default='text')
    outcome = models.CharField(max_length=20, default='completed')
    time_spent = models.IntegerField(default=0)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'app_name']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.app_name} - {self.activity_type}"

class ScreenTimeLog(models.Model):
    """
    Tracks precise session-based usage of tools and courses.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='screen_time_logs')
    course = models.ForeignKey('course.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='screen_time_logs')
    tool_name = models.CharField(max_length=50) # e.g., 'ai_tutor', 'quiz', 'flashcards'
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'tool_name']),
            models.Index(fields=['started_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.tool_name} ({self.duration_seconds}s)"
