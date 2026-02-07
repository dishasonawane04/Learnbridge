from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'core'

urlpatterns = [
    # Original views
    path('dashboard/', views.dashboard, name='dashboard'),
    path('role-select/', views.role_selection, name='role_selection'),
]
