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

class Question(models.Model):
    """
    Curated question bank for reliable, scenario-based assessment
    """
    text = models.TextField()
    options = models.JSONField(default=list) # List of strings
    correct_answer = models.CharField(max_length=255)
    explanation = models.TextField(blank=True)
    difficulty = models.CharField(max_length=20, choices=[
        ('Foundation', 'Foundation'),
        ('Developing', 'Developing'), 
        ('Proficient', 'Proficient'),
        ('Advanced', 'Advanced'),
        ('Mastery', 'Mastery')
    ])
    topic = models.CharField(max_length=100)
    is_scenario_based = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} ({self.difficulty}): {self.text[:50]}..."
