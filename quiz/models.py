from django.db import models
from django.contrib.auth.models import User

class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts', null=True, blank=True)
    course = models.ForeignKey('course.Course', on_delete=models.CASCADE, related_name='quiz_attempts', null=True, blank=True)
    subject = models.CharField(max_length=100)
    score = models.IntegerField()
    total = models.IntegerField()
    percentage = models.FloatField()
    accuracy = models.FloatField(default=0.0)
    difficulty = models.CharField(max_length=20, default='Medium')
    generated_questions = models.JSONField(default=list, blank=True, help_text="Stored original questions for this specific attempt")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.score}/{self.total} ({self.percentage}%)"

    class Meta:
        ordering = ['-created_at']

class Quiz(models.Model):
    course = models.ForeignKey('course.Course', on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    explanation = models.TextField(blank=True, help_text="AI-generated or manual explanation for the correct answer")

    def __str__(self):
        return self.question_text[:50]

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_correct:
            # Set all other options for this question to False
            qs = Option.objects.filter(question=self.question)
            if self.id:
                qs = qs.exclude(id=self.id)
            qs.update(is_correct=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.option_text

class StudentQuestionHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey('course.Course', on_delete=models.CASCADE)
    question_hash = models.CharField(max_length=64, db_index=True)
    asked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course', 'question_hash')

class StudentAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question_text = models.TextField()
    selected_option = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=255)
    is_correct = models.BooleanField()
    explanation = models.TextField(blank=True)
