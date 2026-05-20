from django import forms

from .models import Note


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["title", "content", "color", "category", "priority", "is_pinned", "date"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Rent reminder, trip plan, grocery idea..."}),
            "content": forms.Textarea(attrs={"rows": 8, "placeholder": "Write the useful details here..."}),
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
