from django.urls import path
from . import views

urlpatterns = [
    path('', views.ai_home, name='ai_home'),
]
