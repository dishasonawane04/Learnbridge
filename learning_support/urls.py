from django.urls import path
from . import views

urlpatterns = [
    path('', views.support_home, name='support_home'),
    path('new/', views.new_support_chat, name='new_support_chat'),
    path('api/chat/', views.support_chat_api, name='support_chat_api'),
]
