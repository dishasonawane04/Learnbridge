from django.urls import path
from . import views

urlpatterns = [
    path('', views.subjects_view, name='quiz_subjects'),
    path('start/', views.quiz_view, name='quiz_start'),
]
