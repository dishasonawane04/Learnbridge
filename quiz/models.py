from django.db import models
from django.contrib.auth.models import User

class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts', null=True, blank=True)
    course = models.ForeignKey('course.Course', on_delete=models.CASCADE, related_name='quiz_attempts', null=True, blank=True)
    subject = models.CharField(max_length=100)
    score = models.IntegerField()
    total = models.IntegerField()
    percentage = models.FloatField()
    difficulty = models.CharField(max_length=20, default='Medium')
    generated_questions = models.JSONField(default=list, blank=True, help_text="Stored questions for review")
    used_chunk_ids = models.JSONField(default=list, blank=True, help_text="IDs of KnowledgeStore chunks used in this quiz")
    failed_topics = models.JSONField(default=list, blank=True, help_text="Metadata from failed questions for summary")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.score}/{self.total} ({self.percentage}%)"

    class Meta:
        ordering = ['-created_at']
