from django.contrib import admin
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model

# Customize Django admin branding
admin.site.site_header = "Wenster"
admin.site.site_title = "Wenster"
admin.site.index_title = "Адміністрування"


def _wenster_admin_has_permission(request):
    user = request.user
    if not user.is_active:
        return False
    if user.is_superuser:
        return True
    return user.is_staff and not getattr(user, "is_manager", False)


admin.site.has_permission = _wenster_admin_has_permission


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("session_key", "user_email", "expire_date")
    list_filter = ("expire_date",)
    search_fields = ("session_key",)

    def user_email(self, obj):
        try:
            data = obj.get_decoded()
            uid = data.get("_auth_user_id")
            if not uid:
                return "—"
            User = get_user_model()
            user = User.objects.filter(pk=uid).first()
            return getattr(user, "email", f"ID {uid}") if user else f"ID {uid}"
        except Exception:
            return "—"

    user_email.short_description = "Користувач"
