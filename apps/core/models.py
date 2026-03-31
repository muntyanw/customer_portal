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


class ResourceLink(models.Model):
    TYPE_TECHNICAL = "technical"
    TYPE_VIDEO = "video"
    TYPE_CHOICES = (
        (TYPE_TECHNICAL, "Технічна інформація"),
        (TYPE_VIDEO, "Відео"),
    )

    resource_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    url = models.URLField(blank=True)
    attachment = models.FileField(upload_to="technical_info_files/", blank=True, null=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "title", "-created_at"]
        verbose_name = "Матеріал"
        verbose_name_plural = "Матеріали"

    def __str__(self):
        return f"{self.get_resource_type_display()}: {self.title}"

    @property
    def attachment_url(self):
        return self.attachment.url if self.attachment else ""
