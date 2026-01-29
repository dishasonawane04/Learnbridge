from django.contrib import admin
from .models import UserProfile, UserActivity

admin.site.register(UserProfile)
admin.site.register(UserActivity)
