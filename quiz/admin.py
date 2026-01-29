from django.contrib import admin
from .models import QuizAttempt

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['subject', 'score', 'total', 'percentage', 'created_at']
    list_filter = ['subject', 'created_at']
    search_fields = ['subject']
    ordering = ['-created_at']
