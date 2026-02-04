from django.urls import path
from . import views

app_name = 'learning_support'

urlpatterns = [
    path('', views.support_home, name='support_home'),
    path('new/', views.new_support_chat, name='new_support_chat'),
    path('api/chat/', views.support_chat_api, name='support_chat_api'),
    path('start-unit/<int:unit_id>/', views.start_unit_support, name='start_unit_support'),
]
