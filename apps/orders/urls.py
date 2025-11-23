from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("", views.order_list, name="list"),
    path("create/", views.order_create, name="create"),

    # создание нового заказа
    path("builder/", views.order_builder, name="builder"),  # 👈 тут ИМЯ "builder"
    path("builder/<int:pk>/", views.order_builder, name="builder_edit"),
    path("<int:pk>/", views.order_detail, name="detail"),
    path("<int:pk>/edit/", views.order_update, name="update"),
    path("<int:pk>/delete/", views.order_delete, name="delete"),

]
