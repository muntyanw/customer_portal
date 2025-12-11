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
    full_name = forms.CharField(label="ПІБ", required=False)
    phone = forms.CharField(label="Телефон", required=True)
    contact_email = forms.EmailField(label="Email (контактний)", required=False)
    note = forms.CharField(label="Примітка", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    credit_allowed = forms.BooleanField(label="Кредит дозволено", required=False)
    avatar = forms.ImageField(label="Аватар", required=False)
    is_manager = forms.BooleanField(label="Роль: менеджер", required=False)

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop("user_instance")
        self.profile_instance = kwargs.pop("profile_instance")
        can_edit_credit = kwargs.pop("can_edit_credit", False)
        can_edit_role = kwargs.pop("can_edit_role", False)
        super().__init__(*args, **kwargs)
        self.fields["email"].initial = self.user_instance.email
        self.fields["full_name"].initial = self.profile_instance.full_name
        self.fields["phone"].initial = self.profile_instance.phone
        self.fields["contact_email"].initial = self.profile_instance.contact_email
        self.fields["note"].initial = self.profile_instance.note
        self.fields["credit_allowed"].initial = self.profile_instance.credit_allowed
        self.fields["avatar"].initial = self.profile_instance.avatar
        if not can_edit_credit:
            self.fields.pop("credit_allowed", None)
        if can_edit_role:
            self.fields["is_manager"].initial = bool(getattr(self.user_instance, "is_manager", False))
        else:
            self.fields.pop("is_manager", None)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": "form-control"})
            else:
                if not isinstance(field.widget, forms.FileInput):
                    field.widget.attrs.update({"class": "form-control"})

    def save(self):
        self.user_instance.email = self.cleaned_data["email"]
        self.user_instance.username = self.cleaned_data["email"]
        update_fields = ["email", "username"]
        if "is_manager" in self.cleaned_data:
            self.user_instance.is_manager = bool(self.cleaned_data.get("is_manager", False))
            update_fields.append("is_manager")
        self.user_instance.save(update_fields=update_fields)

        self.profile_instance.full_name = self.cleaned_data.get("full_name", "")
        self.profile_instance.phone = self.cleaned_data.get("phone", "")
        self.profile_instance.contact_email = self.cleaned_data.get("contact_email", "")
        self.profile_instance.note = self.cleaned_data.get("note", "")
        if "credit_allowed" in self.cleaned_data:
            self.profile_instance.credit_allowed = self.cleaned_data.get("credit_allowed", False)
        if self.cleaned_data.get("avatar"):
            self.profile_instance.avatar = self.cleaned_data["avatar"]
        self.profile_instance.save()
        return self.user_instance

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    def clean(self):
        cleaned = super().clean()
        user = authenticate(username=cleaned.get("email"), password=cleaned.get("password"))
        if not user:
            raise forms.ValidationError("Invalid credentials")
        cleaned["user"] = user
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
