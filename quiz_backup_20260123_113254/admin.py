from django.contrib import admin
from .models import QuizAttempt

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('topic', 'difficulty', 'score', 'percentage', 'created_at')
    list_filter = ('topic', 'difficulty', 'created_at')
    ordering = ('-created_at',)
