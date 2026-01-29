from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLES, default='student')
    
    def __str__(self):
        return f"{self.user.username} ({self.role})"

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    app_name = models.CharField(max_length=50)  # ai_tutor, quiz, learning_support, etc.
    topic = models.CharField(max_length=100)
    input_type = models.CharField(max_length=20) # text, image
    time_spent = models.IntegerField(help_text="Time spent in seconds")
    quiz_score = models.IntegerField(null=True, blank=True)
    outcome = models.CharField(max_length=20) # completed, needs_revision
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "User Activities"

    def __str__(self):
        return f"{self.user.username} - {self.app_name} - {self.topic}"
