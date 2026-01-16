from django.db import models

class QuizAttempt(models.Model):
    topic = models.CharField(max_length=100)
    difficulty = models.CharField(max_length=50)
    score = models.IntegerField()
    total = models.IntegerField()
    percentage = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} - {self.difficulty} - {self.percentage:.1f}%"
