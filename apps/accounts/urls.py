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
    path("profile/<int:pk>/delete/", views.client_delete_view, name="profile_delete"),
    path("profile/<int:pk>/restore/", views.client_restore_view, name="profile_restore"),
    path("clients/", views.clients_list_view, name="clients_list"),
    path("clients/trash/", views.clients_trash_view, name="clients_trash"),
    path("clients/new/", views.client_create_view, name="client_create"),
]
