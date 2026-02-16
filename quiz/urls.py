from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path('', views.subjects_view, name='quiz_subjects'),
    path('start/', views.quiz_view, name='quiz_start'),
    path('start-unit/<int:unit_id>/', views.start_unit_quiz, name='start_unit_quiz'),
    path('start-unit/<int:unit_id>/', views.start_unit_quiz, name='start_unit_quiz'),
]
