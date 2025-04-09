from django.contrib import admin
from django.urls import path,include
from .views import MedicalChatBotView
urlpatterns = [
    path("chatbot/",MedicalChatBotView.as_view(),name="chatbot")
    
]