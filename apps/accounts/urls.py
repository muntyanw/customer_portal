from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/<int:pk>/", views.profile_view, name="profile_other"),
    path("profile/<int:pk>/password/", views.client_password_change_view, name="profile_password_change"),
    path("clients/", views.clients_list_view, name="clients_list"),
    path("clients/new/", views.client_create_view, name="client_create"),
]
