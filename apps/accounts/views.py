from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from .forms import RegisterForm, LoginForm, ProfileForm
from .models import User
from apps.customers.models import CustomerProfile
from apps.accounts.roles import is_manager
from apps.accounts.forms import ClientCreateForm

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.username = user.email
            user.save()
            CustomerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": form.cleaned_data.get("full_name", ""),
                    "phone": form.cleaned_data.get("phone", ""),
                    "contact_email": form.cleaned_data.get("email", ""),
                },
            )
            login(request, user)
            return redirect("core:dashboard")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            login(request, form.cleaned_data["user"])
            return redirect("core:dashboard")
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form})

@login_required
def profile_view(request, pk=None):
    target_user = request.user
    if pk:
        if not is_manager(request.user):
            messages.error(request, "Доступ заборонено.")
            return redirect("accounts:profile")
        target_user = get_object_or_404(User, pk=pk)

    profile, _ = CustomerProfile.objects.get_or_create(user=target_user)

    can_edit_credit = is_manager(request.user)
    can_edit_role = is_manager(request.user)

    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            request.FILES,
            user_instance=target_user,
            profile_instance=profile,
            can_edit_credit=can_edit_credit,
            can_edit_role=can_edit_role,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Профіль оновлено.")
            if pk:
                return redirect("accounts:profile_other", pk=pk)
            return redirect("accounts:profile")
    else:
        form = ProfileForm(
            user_instance=target_user,
            profile_instance=profile,
            can_edit_credit=can_edit_credit,
            can_edit_role=can_edit_role,
        )

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "target_user": target_user,
            "can_edit_credit": can_edit_credit,
            "can_edit_role": can_edit_role,
        },
    )

def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@login_required
def clients_list_view(request):
    if not is_manager(request.user):
        messages.error(request, "Доступ заборонено.")
        return redirect("core:dashboard")

    if request.method == "POST" and request.POST.get("action") == "toggle_credit":
        user_id = request.POST.get("user_id")
        target_user = get_object_or_404(User, pk=user_id)
        profile, _ = CustomerProfile.objects.get_or_create(user=target_user)
        profile.credit_allowed = bool(request.POST.get("credit_allowed"))
        profile.save(update_fields=["credit_allowed"])
        messages.success(request, "Статус кредиту оновлено.")
        return redirect("accounts:clients_list")
    if request.method == "POST" and request.POST.get("action") == "toggle_manager":
        user_id = request.POST.get("user_id")
        target_user = get_object_or_404(User, pk=user_id)
        target_user.is_manager = bool(request.POST.get("is_manager"))
        target_user.save(update_fields=["is_manager"])
        messages.success(request, "Роль менеджера оновлено.")
        return redirect("accounts:clients_list")

    sort = request.GET.get("sort", "email")
    direction = ""
    if sort.startswith("-"):
        direction = "-"
        sort_field = sort[1:]
    else:
        sort_field = sort
    allowed_sorts = {"email": "email", "full_name": "customerprofile__full_name", "phone": "customerprofile__phone"}
    order_field = allowed_sorts.get(sort_field, "email")
    ordering = f"{direction}{order_field}"

    q = request.GET.get("q", "").strip()

    users_qs = (
        User.objects.filter(is_customer=True)
        .select_related("customerprofile")
    )
    if q:
        users_qs = users_qs.filter(
            models.Q(email__icontains=q)
            | models.Q(customerprofile__full_name__icontains=q)
            | models.Q(customerprofile__phone__icontains=q)
        )

    users_qs = users_qs.order_by(ordering)

    context = {
        "clients": users_qs,
        "sort": sort,
        "q": q,
        "next_sort": lambda field: (f"-{field}" if sort == field else field),
    }
    return render(request, "accounts/clients_list.html", context)


@login_required
def client_create_view(request):
    if not is_manager(request.user):
        messages.error(request, "Доступ заборонено.")
        return redirect("core:dashboard")

    if request.method == "POST":
        form = ClientCreateForm(request.POST)
        if form.is_valid():
            user = User.objects.create(
                email=form.cleaned_data["email"],
                username=form.cleaned_data["email"],
                is_customer=True,
                is_manager=False,
            )
            user.set_password(form.cleaned_data["password"])
            user.save()
            CustomerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": form.cleaned_data.get("full_name", ""),
                    "phone": form.cleaned_data.get("phone", ""),
                    "contact_email": form.cleaned_data.get("contact_email", ""),
                    "note": form.cleaned_data.get("note", ""),
                },
            )
            messages.success(request, "Клієнта створено.")
            return redirect("accounts:clients_list")
    else:
        form = ClientCreateForm()
    return render(request, "accounts/client_create.html", {"form": form})
