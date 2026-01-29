from django.db import models

class QuizAttempt(models.Model):
    subject = models.CharField(max_length=100)
    score = models.IntegerField()
    total = models.IntegerField()
    percentage = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.score}/{self.total} ({self.percentage}%)"

    class Meta:
        ordering = ['-created_at']
