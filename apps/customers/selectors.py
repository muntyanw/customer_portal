from django.contrib.auth import get_user_model

from apps.customers.models import CustomerProfile


def customer_ordering_fields(prefix="customerprofile__"):
    return [
        f"{prefix}company_name",
        f"{prefix}full_name",
        "email" if prefix == "customerprofile__" else f"{prefix}user__email",
    ]


def customer_users_queryset(*, with_orders=False):
    User = get_user_model()
    qs = (
        User.objects.filter(is_customer=True, is_active=True)
        .select_related("customerprofile")
    )
    if with_orders:
        qs = qs.filter(orders__isnull=False).distinct()
    return qs.order_by(*customer_ordering_fields())


def customer_profiles_queryset():
    return (
        CustomerProfile.objects.select_related("user")
        .filter(user__is_active=True, user__is_customer=True)
        .order_by(*customer_ordering_fields(prefix=""))
    )
