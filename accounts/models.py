from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('Student', 'Student'),
        ('Faculty', 'Faculty'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='account_profile')
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
