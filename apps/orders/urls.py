# apps/orders/urls.py
from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    # ----- Ролети -----
    path("", views.order_list, name="list"),
    #path("create/", views.order_create, name="create"),

    # билдер ролет
    path("builder/", views.order_builder, name="builder"),
    path("builder/<int:pk>/", views.order_builder, name="builder_edit"),

    path("<int:pk>/", views.order_detail, name="detail"),
    path("<int:pk>/edit/", views.order_update, name="update"),
    path("<int:pk>/delete/", views.order_delete, name="delete"),

    # ----- Комплектуючі -----
    # список заказов с комплектующими
    path("components/", views.order_components_list, name="components_list"),

    # создать новый заказ (с комплектующими) и перейти в билдер
    path(
        "components/builder/",
        views.order_components_builder_new,
        name="components_builder_create",
    ),

    # редактировать/просматривать комплектующие для конкретного заказа
    path(
        "components/builder/<int:pk>/",
        views.order_components_builder,
        name="components_builder",
    ),
    
     path(
        "currency/update-eur/",
        views.update_eur_rate_view,
        name="update_eur_rate",
    ),
]
