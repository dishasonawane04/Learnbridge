from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'core'

urlpatterns = [
    # Original views
    path('dashboard/', views.dashboard, name='dashboard'),
    path('role-select/', views.role_selection, name='role_selection'),
    path('set-active-course/', views.set_active_course, name='set_active_course'),
    path('api/user/active-course/', views.active_course_api, name='active_course_api'),
]
