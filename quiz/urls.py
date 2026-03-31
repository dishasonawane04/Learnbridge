from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path('', views.subjects_view, name='quiz_subjects'),
    path('start/', views.quiz_view, name='quiz_start'),
    path('start-unit/<int:unit_id>/', views.start_unit_quiz, name='start_unit_quiz'),
    path('start-unit/<int:unit_id>/', views.start_unit_quiz, name='start_unit_quiz'),
    path('api/user/courses/', views.user_courses_api, name='user_courses_api'),
    path('api/generate-stream/<int:course_id>/', views.quiz_stream_api, name='quiz_stream_api'),
    path('generate-file/<int:file_id>/', views.generate_quiz_file, name='generate_quiz_file'),
    path('api/save-streamed-questions/', views.save_streamed_questions, name='save_streamed_questions'),
    path('submit-result/', views.submit_quiz, name='submit_quiz'),
    path('create-manual/<int:course_id>/', views.create_quiz_manual, name='create_quiz_manual'),
]
