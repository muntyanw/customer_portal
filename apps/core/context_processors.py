from .models import News


def news_unread(request):
    """
    EN: Expose whether the user has unread news items.
    UA: Повертає прапорець, чи є непрочитані новини.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"news_unread": False}

    unread_qs = News.objects.filter(is_active=True).exclude(
        acknowledgements__user=user
    )
    unread_count = unread_qs.count()
    return {
        "news_unread": unread_count > 0,
        "news_unread_count": unread_count,
    }
