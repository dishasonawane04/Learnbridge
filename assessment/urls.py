from django.urls import path
from . import views

urlpatterns = [
    path('learning-support/', views.learning_support, name='learning_support'),
]
