from django import forms
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.roles import is_manager
from .models import News, NewsAcknowledgement


class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ["title", "body", "is_active"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


@login_required
def dashboard(request):
    news_qs = News.objects.filter(is_active=True)
    if request.user.is_authenticated:
        acked_ids = NewsAcknowledgement.objects.filter(user=request.user).values_list("news_id", flat=True)
        news_qs = news_qs.exclude(id__in=acked_ids)
    news_items = news_qs.order_by("-created_at")
    return render(request, "core/dashboard.html", {"news_items": news_items})


def _manager_check(user):
    return is_manager(user)


@login_required
@user_passes_test(_manager_check)
def news_list(request):
    news_items = News.objects.all().order_by("-created_at")
    return render(request, "core/news_list.html", {"news_items": news_items})


@login_required
@user_passes_test(_manager_check)
def news_create(request):
    if request.method == "POST":
        form = NewsForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            return redirect("core:news_list")
    else:
        form = NewsForm(initial={"is_active": True})
    return render(request, "core/news_form.html", {"form": form, "is_edit": False})


@login_required
@user_passes_test(_manager_check)
def news_edit(request, pk: int):
    news = get_object_or_404(News, pk=pk)
    if request.method == "POST":
        form = NewsForm(request.POST, instance=news)
        if form.is_valid():
            form.save()
            return redirect("core:news_list")
    else:
        form = NewsForm(instance=news)
    return render(request, "core/news_form.html", {"form": form, "is_edit": True, "news": news})


@login_required
@require_POST
def news_acknowledge(request, pk: int):
    news = get_object_or_404(News, pk=pk, is_active=True)
    NewsAcknowledgement.objects.get_or_create(news=news, user=request.user)
    return redirect("core:dashboard")
