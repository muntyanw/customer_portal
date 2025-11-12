from django.urls import path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

app_name = "core"

@login_required
def dashboard(request):
    return render(request, "core/dashboard.html")

urlpatterns = [
    path("", dashboard, name="dashboard"),
]
