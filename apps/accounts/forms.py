import re
from decimal import Decimal, InvalidOperation
from django import forms
from django.contrib.auth import authenticate
from .models import User
from apps.customers.models import CustomerProfile

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")
    full_name = forms.CharField(required=False, label="ПІБ")
    phone = forms.CharField(required=True, label="Телефон")
    class Meta:
        model = User
        fields = ["email"]
    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords don't match")
        return cleaned


class ProfileForm(forms.Form):
    email = forms.EmailField(label="Email (логін)")
    company_name = forms.CharField(label="Назва компанії", required=True)
    full_name = forms.CharField(label="ПІБ", required=False)
    phone = forms.CharField(label="Телефон", required=True)
    contact_email = forms.EmailField(label="Email (контактний)", required=False)
    trade_address = forms.CharField(label="Адреса торгової точки", required=False)
    delivery_method = forms.ChoiceField(label="Спосіб доставки", required=True, choices=CustomerProfile.DELIVERY_CHOICES)
    delivery_branch = forms.CharField(label="Вантажне відділення (від 200кг)", required=False)
    note = forms.CharField(label="Примітка", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    discount_percent = forms.DecimalField(label="Знижка, %", max_digits=5, decimal_places=2, required=False, min_value=-100, max_value=100)
    credit_allowed = forms.BooleanField(label="Кредит дозволено", required=False)
    avatar = forms.ImageField(label="Аватар", required=False)
    is_manager = forms.BooleanField(label="Роль: менеджер", required=False)

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop("user_instance")
        self.profile_instance = kwargs.pop("profile_instance")
        can_edit_credit = kwargs.pop("can_edit_credit", False)
        can_edit_role = kwargs.pop("can_edit_role", False)
        can_edit_discount = kwargs.pop("can_edit_discount", False)
        self.creating = kwargs.pop("creating", False)
        super().__init__(*args, **kwargs)
        if self.creating:
            self.fields["password"] = forms.CharField(label="Пароль", widget=forms.PasswordInput, required=True)
            self.fields["password2"] = forms.CharField(label="Підтвердити пароль", widget=forms.PasswordInput, required=True)
        self.fields["email"].initial = self.user_instance.email
        self.fields["company_name"].initial = self.profile_instance.company_name
        self.fields["full_name"].initial = self.profile_instance.full_name
        self.fields["phone"].initial = self.profile_instance.phone
        self.fields["contact_email"].initial = self.profile_instance.contact_email
        self.fields["trade_address"].initial = self.profile_instance.trade_address
        self.fields["delivery_method"].initial = self.profile_instance.delivery_method
        self.fields["delivery_branch"].initial = self.profile_instance.delivery_branch
        self.fields["note"].initial = self.profile_instance.note
        self.fields["discount_percent"].initial = self.profile_instance.discount_percent
        self.fields["credit_allowed"].initial = self.profile_instance.credit_allowed
        self.fields["avatar"].initial = self.profile_instance.avatar
        if not can_edit_discount:
            self.fields.pop("discount_percent", None)
        if not can_edit_credit:
            self.fields.pop("credit_allowed", None)
        if can_edit_role:
            self.fields["is_manager"].initial = bool(getattr(self.user_instance, "is_manager", False))
        else:
            self.fields.pop("is_manager", None)
        if self.creating:
            # ensure password fields rendered after other fields
            self.order_fields(list(self.fields.keys()))
        for field in self.fields.values():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": "form-control"})
            else:
                if not isinstance(field.widget, forms.FileInput):
                    field.widget.attrs.update({"class": "form-control"})

    def save(self):
        self.user_instance.email = self.cleaned_data["email"]
        self.user_instance.username = self.cleaned_data["email"]
        is_new = self.user_instance.pk is None
        if "is_manager" in self.cleaned_data:
            self.user_instance.is_manager = bool(self.cleaned_data.get("is_manager", False))
        if self.creating:
            self.user_instance.is_customer = True
            if "password" in self.cleaned_data:
                self.user_instance.set_password(self.cleaned_data["password"])
            self.user_instance.save()
        else:
            update_fields = ["email", "username"]
            if "is_manager" in self.cleaned_data:
                update_fields.append("is_manager")
            self.user_instance.save(update_fields=update_fields)

        self.profile_instance.company_name = self.cleaned_data.get("company_name", "")
        self.profile_instance.full_name = self.cleaned_data.get("full_name", "")
        self.profile_instance.phone = self.cleaned_data.get("phone", "")
        self.profile_instance.contact_email = self.cleaned_data.get("contact_email", "")
        self.profile_instance.trade_address = self.cleaned_data.get("trade_address", "")
        self.profile_instance.delivery_method = self.cleaned_data.get("delivery_method", "")
        self.profile_instance.delivery_branch = self.cleaned_data.get("delivery_branch", "")
        self.profile_instance.note = self.cleaned_data.get("note", "")
        if "credit_allowed" in self.cleaned_data:
            self.profile_instance.credit_allowed = self.cleaned_data.get("credit_allowed", False)
        if "discount_percent" in self.cleaned_data:
            self.profile_instance.discount_percent = Decimal(self.cleaned_data.get("discount_percent") or 0)
        if self.cleaned_data.get("avatar"):
            self.profile_instance.avatar = self.cleaned_data["avatar"]
        if is_new and not getattr(self.profile_instance, "user_id", None):
            self.profile_instance.user = self.user_instance
        self.profile_instance.save()
        return self.user_instance

    def clean(self):
        cleaned = super().clean()
        if self.creating:
            if cleaned.get("password") != cleaned.get("password2"):
                self.add_error("password2", "Паролі не співпадають")
        method = cleaned.get("delivery_method")
        branch = (cleaned.get("delivery_branch") or "").strip()
        if method == CustomerProfile.DELIVERY_NP and not branch:
            self.add_error("delivery_branch", "Вкажіть вантажне відділення для Нової Пошти.")
        return cleaned


class ContactForm(forms.Form):
    contact_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    phone = forms.CharField(label="Номер телефону (логін)", required=False)
    contact_name = forms.CharField(label="Контактне лице", required=False)
    email = forms.EmailField(label="Email", required=False)

    def clean(self):
        cleaned = super().clean()
        phone = (cleaned.get("phone") or "").strip()
        name = (cleaned.get("contact_name") or "").strip()
        if phone or name or (cleaned.get("email") or "").strip():
            if not phone:
                self.add_error("phone", "Вкажіть номер телефону.")
            if not name:
                self.add_error("contact_name", "Вкажіть контактну особу.")
        return cleaned


ContactFormSet = forms.formset_factory(ContactForm, extra=0, can_delete=True)

class LoginForm(forms.Form):
    login = forms.CharField(label="Email або телефон")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")

    def _normalize_phone(self, value: str) -> str:
        return re.sub(r"\D", "", value or "")

    def clean(self):
        cleaned = super().clean()
        login_value = (cleaned.get("login") or "").strip()
        password = cleaned.get("password")

        user = None
        auth_user = None

        if "@" in login_value:
            user = User.objects.filter(email__iexact=login_value).first()
        else:
            norm = self._normalize_phone(login_value)
            if len(norm) != 10:
                raise forms.ValidationError("Введіть телефон у форматі 063-435-00-81.")
            profile = None
            for p in CustomerProfile.objects.filter(phone__isnull=False).select_related("user"):
                if self._normalize_phone(p.phone) == norm:
                    profile = p
                    break
            if profile:
                user = profile.user

        if user:
            auth_user = authenticate(username=user.username, password=password)

        if not auth_user:
            raise forms.ValidationError("Невірний email/телефон або пароль.")

        cleaned["user"] = auth_user
        return cleaned


class ClientCreateForm(forms.Form):
    email = forms.EmailField(label="Email (логін)", required=True)
    phone = forms.CharField(label="Телефон", required=True)
    full_name = forms.CharField(label="ПІБ", required=False)
    contact_email = forms.EmailField(label="Email (контактний)", required=False)
    note = forms.CharField(label="Примітка", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(label="Підтвердити пароль", widget=forms.PasswordInput, required=True)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password2"):
            raise forms.ValidationError("Паролі не співпадають")
        return cleaned
