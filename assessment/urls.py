from django.urls import path
from . import views

app_name = 'assessment'

urlpatterns = [
    path('learning-support/', views.learning_support, name='learning_support'),
]
