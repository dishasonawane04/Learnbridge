from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('faculty/', views.faculty_dashboard, name='faculty_dashboard'),
    path('faculty/student-performance/', views.faculty_student_performance, name='faculty_student_performance'),
    path('faculty/student/<int:user_id>/', views.faculty_student_detail, name='faculty_student_detail'),
    path('faculty/screen-time/', views.faculty_screen_time_view, name='faculty_screen_time'),
    path('faculty/consistency/', views.faculty_consistency_view, name='faculty_consistency'),
    path('faculty/quiz-history/<int:user_id>/', views.faculty_quiz_history, name='faculty_quiz_history'),
    path('faculty/quiz-attempt/<int:attempt_id>/', views.faculty_quiz_attempt_detail, name='faculty_quiz_attempt_detail'),
    path('api/track-screen-time/', views.track_screen_time_api, name='api_track_screen_time'),
]
