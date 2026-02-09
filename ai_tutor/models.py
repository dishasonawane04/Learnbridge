from django.db import models
from django.contrib.auth.models import User
import uuid

class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    course = models.ForeignKey('course.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='chats')
    unit = models.ForeignKey('course.CourseUnit', on_delete=models.SET_NULL, null=True, blank=True, related_name='chats')
    session_key = models.CharField(max_length=40, null=True, blank=True)
    title = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    share_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return self.title

class ChatMessage(models.Model):
    chat = models.ForeignKey(Chat, related_name='messages', on_delete=models.CASCADE)
    sender = models.CharField(max_length=10, choices=[('user', 'User'), ('ai', 'AI')])
    content = models.TextField(blank=True)
    msg_type = models.CharField(max_length=10, default='text', choices=[('text', 'Text'), ('image', 'Image'), ('doc', 'Document'), ('voice', 'Voice')])
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender}: {self.content[:20]}..."
