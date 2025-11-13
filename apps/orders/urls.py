from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("", views.order_list, name="list"),
    path("create/", views.order_create, name="create"),
    path("builder/", views.order_builder, name="builder"),  # ← вот этот новый путь
    path("<int:pk>/", views.order_detail, name="detail"),
    path("<int:pk>/edit/", views.order_update, name="update"),
]
