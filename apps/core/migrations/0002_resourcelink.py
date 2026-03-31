from django.db import migrations, models


def seed_resource_links(apps, schema_editor):
    ResourceLink = apps.get_model("core", "ResourceLink")
    try:
        from apps.core.link_data.resource_links import TECHNICAL_INFO_LINKS, VIDEO_LINKS
    except Exception:
        TECHNICAL_INFO_LINKS = []
        VIDEO_LINKS = []

    for index, item in enumerate(TECHNICAL_INFO_LINKS):
        url = (item.get("url") or "").strip()
        if not url:
            continue
        ResourceLink.objects.get_or_create(
            resource_type="technical",
            url=url,
            defaults={
                "title": (item.get("title") or "Файл").strip() or "Файл",
                "description": (item.get("description") or "").strip(),
                "sort_order": index,
                "is_active": True,
            },
        )

    for index, item in enumerate(VIDEO_LINKS):
        url = (item.get("url") or "").strip()
        if not url:
            continue
        ResourceLink.objects.get_or_create(
            resource_type="video",
            url=url,
            defaults={
                "title": (item.get("title") or "Відео").strip() or "Відео",
                "description": (item.get("description") or "").strip(),
                "sort_order": index,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_news"),
    ]

    operations = [
        migrations.CreateModel(
            name="ResourceLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resource_type", models.CharField(choices=[("technical", "Технічна інформація"), ("video", "Відео")], max_length=20)),
                ("title", models.CharField(max_length=255)),
                ("url", models.URLField()),
                ("description", models.TextField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Матеріал",
                "verbose_name_plural": "Матеріали",
                "ordering": ["sort_order", "title", "-created_at"],
            },
        ),
        migrations.RunPython(seed_resource_links, migrations.RunPython.noop),
    ]
