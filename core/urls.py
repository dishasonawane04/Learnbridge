from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'core'

urlpatterns = [
    # Original views
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/faculty/', views.faculty_dashboard, name='faculty_dashboard'),
    
    path('role-select/', views.role_selection, name='role_selection'),
    path('set-active-course/', views.set_active_course, name='set_active_course'),
    path('api/user/active-course/', views.active_course_api, name='active_course_api'),
    
    # Task Assignments
    path('dashboard/faculty/tasks/create/', views.create_task_assignment, name='create_task_assignment'),
    path('dashboard/student/tasks/<int:submission_id>/start/', views.start_task, name='start_task'),
    path('dashboard/student/tasks/<int:submission_id>/complete/', views.complete_task, name='complete_task'),
]
