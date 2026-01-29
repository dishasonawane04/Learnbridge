from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('subjects/', views.subjects_view, name='subjects'),
    path('quiz/', views.quiz, name='quiz'),
]
