from django.contrib import admin

from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "color", "date", "updated_at"]
    list_filter = ["color", "date", "updated_at"]
    search_fields = ["title", "content", "user__username"]
    ordering = ["-updated_at"]
