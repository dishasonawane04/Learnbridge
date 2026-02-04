from django.urls import path
from . import views

urlpatterns = [
<<<<<<< HEAD:ai_tutor/urls.py
    path('', views.tutor_home, name='tutor_home'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/new_chat/', views.new_chat, name='new_chat'),
    path('api/chat/<uuid:chat_id>/history/', views.load_chat_history, name='load_chat_history'),
    path('api/chat/<uuid:chat_id>/rename/', views.rename_chat, name='rename_chat'),
    path('api/chat/<uuid:chat_id>/delete/', views.delete_chat, name='delete_chat'),
    path('api/chat/<uuid:chat_id>/archive/', views.archive_chat, name='archive_chat'),
    path('api/chat/<uuid:chat_id>/pin/', views.pin_chat, name='pin_chat'),
    path('api/chat/<uuid:chat_id>/share-link/', views.get_share_link, name='get_share_link'),
    path('archived/', views.archived_chats, name='archived_chats'),
    path('share/<uuid:token>/', views.shared_chat, name='shared_chat'),
=======
    path('generate/', views.study_plan, name='study_plan'),
>>>>>>> a308bc6ddc579d8c8c7d185a879f27e44969e3b4:generator/urls.py
]
