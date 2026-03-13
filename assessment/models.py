from django.db import models
from django.contrib.auth.models import User
from course.models import Course

class PracticeAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    total_questions = models.IntegerField(default=0)
    feedback_summary = models.TextField(blank=True)
    weak_areas = models.JSONField(default=list, blank=True)
    recommendations = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class PracticeQuestion(models.Model):
    attempt = models.ForeignKey(PracticeAttempt, related_name='questions', on_delete=models.CASCADE)
    q_type = models.CharField(max_length=20) # mcq, short, concept
    question_text = models.TextField()
    options = models.JSONField(default=list, blank=True) # For MCQs
    correct_answer = models.TextField()
    topic = models.CharField(max_length=255, blank=True)

class PracticeAnswer(models.Model):
    attempt = models.ForeignKey(PracticeAttempt, related_name='answers', on_delete=models.CASCADE)
    question = models.ForeignKey(PracticeQuestion, on_delete=models.CASCADE)
    user_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    score_awarded = models.FloatField(default=0.0) # E.g., 0.5 for partial
    ai_explanation = models.TextField(blank=True)

