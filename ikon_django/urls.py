"""Stable React and SireSoft-IKON v1 routes, now served by Django."""
from django.urls import path
from . import views

urlpatterns = [
    path('api/health', views.frontend_health, name='frontend_health'),
    path('api/chat/stream', views.frontend_chat_stream, name='frontend_chat_stream'),
    path('v1/health', views.health, name='health'),
    path('v1/chat', views.chat, name='chat'),
    path('v1/generate', views.generate, name='generate'),
    path('v1/retrieve', views.retrieve, name='retrieve'),
    path('v1/embed', views.embed, name='embed'),
]
