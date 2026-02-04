from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class SupportSession(models.Model):
    """Represents a chat session in the Learning Support app."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_sessions', null=True, blank=True)
    unit = models.ForeignKey('course.CourseUnit', on_delete=models.SET_NULL, null=True, blank=True, related_name='support_sessions')
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    title = models.CharField(max_length=255, default="New Support Session")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

class SupportMessage(models.Model):
    """Individual messages within a support session."""
    SENDER_CHOICES = [('user', 'User'), ('ai', 'AI')]
    
    session = models.ForeignKey(SupportSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class SupportInteraction(models.Model):
    """Logs interactions with the Learning Support AI for analytics."""
    topic = models.CharField(max_length=255, help_text="Topic where help was requested")
    hints_used = models.IntegerField(default=0, help_text="Number of hints provided")
    time_spent_seconds = models.IntegerField(default=0, help_text="Time spent in support session")
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.topic} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
