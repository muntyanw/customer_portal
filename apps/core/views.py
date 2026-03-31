from django import forms
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import OperationalError, ProgrammingError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from apps.accounts.roles import is_manager
from .models import News, NewsAcknowledgement, ResourceLink
from .link_data.resource_links import TECHNICAL_INFO_LINKS, VIDEO_LINKS


class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ["title", "body", "is_active"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ResourceLinkForm(forms.ModelForm):
    class Meta:
        model = ResourceLink
        fields = ["title", "url", "attachment", "description", "sort_order"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Назва"}),
            "url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "attachment": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Короткий опис"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }

    def clean(self):
        cleaned = super().clean()
        url = cleaned.get("url")
        attachment = cleaned.get("attachment")
        if not url and not (attachment or getattr(self.instance, "attachment", None)):
            raise forms.ValidationError("Вкажіть посилання або завантажте файл.")
        return cleaned


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
def news_list(request):
    can_manage = _manager_check(request.user)
    if can_manage:
        news_items = News.objects.all().order_by("-created_at")
    else:
        news_items = News.objects.filter(is_active=True).order_by("-created_at")

    # Mark visible active news as read when user opens the News page.
    visible_active_ids = news_items.filter(is_active=True).exclude(
        acknowledgements__user=request.user
    ).values_list("id", flat=True)
    unread_ids = list(visible_active_ids)
    if unread_ids:
        NewsAcknowledgement.objects.bulk_create(
            [NewsAcknowledgement(news_id=news_id, user=request.user) for news_id in unread_ids],
            ignore_conflicts=True,
        )

    return render(request, "core/news_list.html", {"news_items": news_items, "can_manage": can_manage})


@login_required
@user_passes_test(_manager_check, login_url="core:news_list")
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
@user_passes_test(_manager_check, login_url="core:news_list")
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


def _youtube_video_id(url: str) -> str:
    parsed = urlparse((url or "").strip())
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").strip("/")
    if "youtu.be" in host:
        return path
    if "youtube.com" in host:
        if path == "watch":
            return (parse_qs(parsed.query).get("v") or [""])[0]
        if path.startswith("embed/"):
            return path.split("/", 1)[1]
        if path.startswith("shorts/"):
            return path.split("/", 1)[1]
    return ""


def _resource_page_context(resource_type: str, page_title: str):
    try:
        links = list(ResourceLink.objects.filter(resource_type=resource_type, is_active=True))
    except (ProgrammingError, OperationalError):
        links = []
    if not links:
        fallback_source = TECHNICAL_INFO_LINKS if resource_type == ResourceLink.TYPE_TECHNICAL else VIDEO_LINKS
        links = [
            {
                "title": (item.get("title") or "").strip(),
                "url": (item.get("url") or "").strip(),
                "description": (item.get("description") or "").strip(),
                "attachment_url": "",
                "video_id": _youtube_video_id((item.get("url") or "").strip()) if resource_type == ResourceLink.TYPE_VIDEO else "",
            }
            for item in fallback_source
            if (item.get("url") or "").strip()
        ]
    else:
        for item in links:
            item.video_id = _youtube_video_id(item.url) if resource_type == ResourceLink.TYPE_VIDEO else ""

    return {
        "page_title": page_title,
        "page_heading": page_title,
        "resource_type": resource_type,
        "links": links,
        "is_video_page": resource_type == ResourceLink.TYPE_VIDEO,
    }


@login_required
def technical_info_links(request):
    can_manage = request.user.is_superuser
    edit_id = (request.GET.get("edit") or request.POST.get("edit_id") or "").strip()
    edit_obj = None
    if edit_id and can_manage:
        try:
            edit_obj = ResourceLink.objects.get(pk=edit_id, resource_type=ResourceLink.TYPE_TECHNICAL)
        except (ResourceLink.DoesNotExist, ProgrammingError, OperationalError):
            edit_obj = None
    form = ResourceLinkForm(request.POST or None, request.FILES or None, instance=edit_obj)
    if request.method == "POST":
        if not can_manage:
            messages.error(request, "Доступ заборонено.")
            return redirect("core:technical_info")
        if form.is_valid():
            obj = form.save(commit=False)
            obj.resource_type = ResourceLink.TYPE_TECHNICAL
            obj.is_active = True
            obj.save()
            messages.success(request, "Посилання оновлено." if edit_obj else "Посилання додано.")
            return redirect("core:technical_info")

    context = _resource_page_context(ResourceLink.TYPE_TECHNICAL, "Технічна інформація")
    context.update({
        "can_manage_links": can_manage,
        "form": form,
        "edit_obj": edit_obj,
    })
    return render(
        request,
        "core/resource_links.html",
        context,
    )


@login_required
def video_links(request):
    can_manage = request.user.is_superuser
    edit_id = (request.GET.get("edit") or request.POST.get("edit_id") or "").strip()
    edit_obj = None
    if edit_id and can_manage:
        try:
            edit_obj = ResourceLink.objects.get(pk=edit_id, resource_type=ResourceLink.TYPE_VIDEO)
        except (ResourceLink.DoesNotExist, ProgrammingError, OperationalError):
            edit_obj = None
    form = ResourceLinkForm(request.POST or None, request.FILES or None, instance=edit_obj)
    if request.method == "POST":
        if not can_manage:
            messages.error(request, "Доступ заборонено.")
            return redirect("core:videos")
        if form.is_valid():
            obj = form.save(commit=False)
            obj.resource_type = ResourceLink.TYPE_VIDEO
            obj.is_active = True
            obj.save()
            messages.success(request, "Посилання оновлено." if edit_obj else "Посилання додано.")
            return redirect("core:videos")

    context = _resource_page_context(ResourceLink.TYPE_VIDEO, "Відео")
    context.update({
        "can_manage_links": can_manage,
        "form": form,
        "edit_obj": edit_obj,
    })
    return render(
        request,
        "core/resource_links.html",
        context,
    )


@login_required
@require_POST
def resource_link_delete(request, pk: int):
    if not request.user.is_superuser:
        messages.error(request, "Доступ заборонено.")
        return redirect("core:dashboard")
    link = get_object_or_404(ResourceLink, pk=pk)
    resource_type = link.resource_type
    link.delete()
    messages.success(request, "Посилання видалено.")
    if resource_type == ResourceLink.TYPE_VIDEO:
        return redirect("core:videos")
    return redirect("core:technical_info")
