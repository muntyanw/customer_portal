from django.conf import settings
from django.db import models


class News(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Новина"
        verbose_name_plural = "Новини"

    def __str__(self):
        return self.title


class NewsAcknowledgement(models.Model):
    news = models.ForeignKey(
        News,
        on_delete=models.CASCADE,
        related_name="acknowledgements",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="news_acknowledgements",
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("news", "user")
        ordering = ["-acknowledged_at"]
        verbose_name = "Ознайомлення з новиною"
        verbose_name_plural = "Ознайомлення з новинами"

    def __str__(self):
        return f"{self.user} -> {self.news}"
