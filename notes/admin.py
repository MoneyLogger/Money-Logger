from django.contrib import admin

from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "color", "date", "updated_at", "is_active"]
    list_filter = ["color", "date", "updated_at", "is_active"]
    search_fields = ["title", "content", "user__username"]
    ordering = ["-updated_at"]

    def get_queryset(self, request):
        return Note.all_objects.all()
