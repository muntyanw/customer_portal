# apps/orders/urls.py
from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    # список ролетів
    path("", views.order_list, name="list"),
    path("all/", views.order_all_list, name="all_list"),

    # список замовлень з комплектуючими
    path("components/", views.order_components_list, name="components_list"),
    path("fabrics/", views.order_fabrics_list, name="fabrics_list"),
    path("balances/", views.balances_history, name="balances"),
    path("balances/export/", views.balances_excel, name="balances_excel"),
    path("balances/page/<str:token>/", views.balance_public_page, name="balance_public"),
    path("balances/users/", views.balances_users, name="balances_users"),
    path("export/", views.order_list_excel, name="orders_excel"),

    # білдер ролетів
    path("builder/", views.order_builder, name="builder"),
    path("builder/<int:pk>/", views.order_builder, name="builder_edit"),
    path("proposal/<str:token>/", views.order_proposal_page, name="proposal_page"),
    path("proposal/<str:token>/excel/", views.order_proposal_excel, name="proposal_excel"),

    # 🔹 створити нове замовлення під комплектуючі
    path(
        "components/builder/",
        views.order_components_builder_new,
        name="components_builder_create",
    ),
    path(
        "fabrics/builder/",
        views.order_fabric_builder_new,
        name="fabrics_builder_create",
    ),

    # 🔹 редагувати комплектуючі для конкретного замовлення
    path(
        "components/builder/<int:pk>/",
        views.order_components_builder,
        name="order_components_builder",   # <-- ЭТО имя использует redirect(...)
    ),
    path(
        "fabrics/builder/<int:pk>/",
        views.order_fabric_builder,
        name="order_fabric_builder",
    ),

    # швидкий перевід у роботу з прев'ю
    path("status/<int:pk>/preview/", views.update_status_preview, name="update_status_preview"),
    path("status/bulk/", views.update_status_bulk, name="update_status_bulk"),

    # транзакції
    path("transactions/new/", views.transaction_create, name="transaction_create"),
    path("transactions/trash/", views.transaction_trash, name="transaction_trash"),
    path("transactions/<int:pk>/restore/", views.transaction_restore, name="transaction_restore"),
    path("transactions/<int:pk>/delete/", views.transaction_delete, name="transaction_delete"),
    path("settings/notifications/", views.order_notifications_settings, name="notifications_settings"),
    path("currency/history/", views.currency_rate_history, name="currency_history"),
    path("<int:pk>/workbook/", views.order_workbook_download, name="workbook_download"),

    # стандартні CRUD для Order
    
    path("<int:pk>/", views.order_detail, name="detail"),
    path("<int:pk>/edit/", views.order_update, name="update"),
    path("<int:pk>/delete/", views.order_delete, name="delete"),
    path("trash/", views.order_trash_list, name="trash"),
    path("trash/<int:pk>/restore/", views.order_restore, name="restore"),
    path("currency/update-eur/", views.update_eur_rate_view, name="update_eur_rate"),
]
