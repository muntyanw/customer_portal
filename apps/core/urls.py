from django.urls import path

app_name = "core"

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("news/", views.news_list, name="news_list"),
    path("news/new/", views.news_create, name="news_create"),
    path("news/<int:pk>/edit/", views.news_edit, name="news_edit"),
    path("news/<int:pk>/ack/", views.news_acknowledge, name="news_ack"),
]
