from django.conf import settings
from django.db import models


class ActiveManager(models.Manager):
    """Only returns active (non-soft-deleted) records."""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Note(models.Model):
    COLOR_CHOICES = (
        ("blue", "Blue"),
        ("purple", "Purple"),
        ("green", "Green"),
        ("yellow", "Yellow"),
        ("red", "Red"),
        ("pink", "Pink"),
    )
    CATEGORY_CHOICES = (
        ("important", "Important"),
        ("goals", "Goals"),
        ("reminder", "Reminder"),
        ("ideas", "Ideas"),
        ("archived", "Archived"),
    )
    PRIORITY_CHOICES = (
        ("high", "High"),
        ("med", "Med"),
        ("low", "Low"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default="blue")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="ideas")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="med")
    is_pinned = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=['user', 'is_active'], name='note_active_idx'),
            models.Index(fields=['user', 'category'], name='note_cat_idx'),
            models.Index(fields=['user', 'is_pinned'], name='note_pin_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"
