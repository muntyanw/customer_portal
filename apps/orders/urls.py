from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    # 🟢 Список ЗАМОВЛЕНЬ РОЛЕТ
    path("", views.order_list, name="list"),

    # 🟢 Список ЗАМОВЛЕНЬ КОМПЛЕКТУЮЧИХ
    path("components/", views.order_components_list, name="components_list"),

    # создание нового заказа (заголовок заказа)
    path("create/", views.order_create, name="create"),

    # билдер роллет
    path("builder/", views.order_builder, name="builder"),
    path("builder/<int:pk>/", views.order_builder, name="builder_edit"),

    # детали / правка / удаление заказа
    path("<int:pk>/", views.order_detail, name="detail"),
    path("<int:pk>/edit/", views.order_update, name="update"),
    path("<int:pk>/delete/", views.order_delete, name="delete"),

    # билдер КОМПЛЕКТУЮЩИХ для конкретного заказа
    path(
        "<int:pk>/components/",
        views.order_components_builder,
        name="order_components_builder",
    ),
]
