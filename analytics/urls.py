from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('faculty/', views.faculty_dashboard, name='faculty_dashboard'),
    path('faculty/student-performance/', views.faculty_student_performance, name='faculty_student_performance'),
    path('faculty/student/<int:user_id>/', views.faculty_student_detail, name='faculty_student_detail'),
]
