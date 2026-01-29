from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Original views
    path('dashboard/', views.dashboard, name='dashboard'),
    path('role-select/', views.role_selection, name='role_selection'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
