from django.urls import path
from . import views

app_name = 'ai_tutor'

urlpatterns = [
    path('', views.tutor_home, name='tutor_home'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('new/', views.new_chat, name='new_chat'),
    path('api/chat/<int:chat_id>/history/', views.load_chat, name='load_chat'),
    path('rename/<int:chat_id>/', views.rename_chat, name='rename_chat'),
    path('delete/<int:chat_id>/', views.delete_chat, name='delete_chat'),
    path('archive/<int:chat_id>/', views.archive_chat, name='archive_chat'),
    path('pin/<int:chat_id>/', views.pin_chat, name='pin_chat'),
    path('archived/', views.archived_chats, name='archived_chats'),
    path('share/<str:token>/', views.shared_chat, name='shared_chat'),
    path('share/link/<int:chat_id>/', views.get_share_link, name='get_share_link'),
    path('unit/<int:unit_id>/', views.start_unit_chat, name='start_unit_chat'),
    path('course/<int:course_id>/', views.start_course_chat, name='start_course_chat'),
    path('ask_voice/', views.ask_voice, name='ask_voice'),
]
