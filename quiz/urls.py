from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path('', views.subjects_view, name='quiz_subjects'),
    path('start/', views.quiz_view, name='quiz_start'),
    path('start-unit/<int:unit_id>/', views.start_unit_quiz, name='start_unit_quiz'),
    path('start-unit/<int:unit_id>/', views.start_unit_quiz, name='start_unit_quiz'),
    path('submit/', views.submit_quiz, name='submit_quiz'),
    path('create-manual/<int:course_id>/', views.create_quiz_manual, name='create_quiz_manual'),
]
