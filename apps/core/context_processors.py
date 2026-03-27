from .models import News
from .link_data.resource_links import TECHNICAL_INFO_LINKS, VIDEO_LINKS


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


def resource_links(request):
    technical_info_url = ""
    video_url = ""
    if TECHNICAL_INFO_LINKS:
        technical_info_url = (TECHNICAL_INFO_LINKS[0].get("url") or "").strip()
    if VIDEO_LINKS:
        video_url = (VIDEO_LINKS[0].get("url") or "").strip()
    return {
        "technical_info_url": technical_info_url,
        "video_url": video_url,
    }
