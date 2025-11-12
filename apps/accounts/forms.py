from django import forms
from django.contrib.auth import authenticate
from .models import User

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")
    class Meta:
        model = User
        fields = ["email"]
    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords don't match")
        return cleaned

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
