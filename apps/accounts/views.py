from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from .forms import RegisterForm, LoginForm, ProfileForm, ContactFormSet
from .models import User
from apps.customers.models import CustomerProfile, CustomerContact
from apps.accounts.roles import is_manager
from apps.orders.views import compute_balance

def register_view(request):
    # Only managers/admins can create accounts via this form
    if not (request.user.is_authenticated and (is_manager(request.user) or request.user.is_staff or request.user.is_superuser)):
        messages.error(request, "Реєстрація доступна лише менеджерам/адмінам.")
        return redirect("accounts:login")

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

    contacts_initial = [
        {"contact_id": c.id, "phone": c.phone, "contact_name": c.contact_name, "email": c.email}
        for c in profile.contacts.all()
    ]

    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            request.FILES,
            user_instance=target_user,
            profile_instance=profile,
            can_edit_credit=can_edit_credit,
            can_edit_role=can_edit_role,
        )
        contact_formset = ContactFormSet(request.POST, prefix="contacts")
        if form.is_valid() and contact_formset.is_valid():
            form.save()
            existing_ids = set()
            for cform in contact_formset:
                data = cform.cleaned_data
                if not data:
                    continue
                contact_id = data.get("contact_id")
                if data.get("DELETE"):
                    if contact_id:
                        CustomerContact.objects.filter(pk=contact_id, profile=profile).delete()
                    continue
                phone = (data.get("phone") or "").strip()
                name = (data.get("contact_name") or "").strip()
                email = (data.get("email") or "").strip()
                if not phone and not name and not email:
                    continue
                if contact_id:
                    CustomerContact.objects.filter(pk=contact_id, profile=profile).update(
                        phone=phone,
                        contact_name=name,
                        email=email,
                    )
                    existing_ids.add(contact_id)
                else:
                    contact = CustomerContact.objects.create(
                        profile=profile,
                        phone=phone,
                        contact_name=name,
                        email=email,
                    )
                    existing_ids.add(contact.id)
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
        contact_formset = ContactFormSet(initial=contacts_initial, prefix="contacts")

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "target_user": target_user,
            "profile_instance": profile,
            "can_edit_credit": can_edit_credit,
            "can_edit_role": can_edit_role,
            "contact_formset": contact_formset,
            "is_creation": False,
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

    clients = list(users_qs)
    balances = {u.id: compute_balance(u, force_personal=True) for u in clients}

    context = {
        "clients": clients,
        "balances": balances,
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

    target_user = User(is_customer=True, is_manager=False)
    profile = CustomerProfile(user=target_user)
    setattr(target_user, "customerprofile", profile)

    can_edit_credit = True
    can_edit_role = True

    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            request.FILES,
            user_instance=target_user,
            profile_instance=profile,
            can_edit_credit=can_edit_credit,
            can_edit_role=can_edit_role,
            creating=True,
        )
        contact_formset = ContactFormSet(request.POST, prefix="contacts")
        if form.is_valid() and contact_formset.is_valid():
            user = form.save()
            profile = getattr(user, "customerprofile", None) or CustomerProfile.objects.get(user=user)
            existing_ids = set()
            for cform in contact_formset:
                data = cform.cleaned_data
                if not data:
                    continue
                if data.get("DELETE"):
                    continue
                phone = (data.get("phone") or "").strip()
                name = (data.get("contact_name") or "").strip()
                email = (data.get("email") or "").strip()
                if not phone and not name and not email:
                    continue
                contact = CustomerContact.objects.create(
                    profile=profile,
                    phone=phone,
                    contact_name=name,
                    email=email,
                )
                existing_ids.add(contact.id)
            messages.success(request, "Клієнта створено.")
            return redirect("accounts:clients_list")
    else:
        form = ProfileForm(
            user_instance=target_user,
            profile_instance=profile,
            can_edit_credit=can_edit_credit,
            can_edit_role=can_edit_role,
            creating=True,
        )
        contact_formset = ContactFormSet(initial=[], prefix="contacts")

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "target_user": target_user,
            "profile_instance": profile,
            "can_edit_credit": can_edit_credit,
            "can_edit_role": can_edit_role,
            "contact_formset": contact_formset,
            "is_creation": True,
        },
    )
