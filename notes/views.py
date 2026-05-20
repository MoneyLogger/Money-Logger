from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import NoteForm
from .models import Note

ARCHIVED_CATEGORY = "archived"
DEFAULT_CATEGORY = "ideas"


@login_required
def notes_list(request):
    category_filter = request.GET.get("category", "")
    search = request.GET.get("q", "").strip()

    notes = Note.objects.filter(user=request.user)
    if category_filter:
        notes = notes.filter(category=category_filter)
    if search:
        notes = notes.filter(Q(title__icontains=search) | Q(content__icontains=search))

    pinned_notes = notes.filter(is_pinned=True)
    regular_notes = notes.filter(is_pinned=False)
    total_notes = notes.count()
    pinned_count = pinned_notes.count()
    archived_count = notes.filter(category="archived").count()

    return render(
        request,
        "notes/notes.html",
        {
            "notes": notes,
            "pinned_notes": pinned_notes,
            "regular_notes": regular_notes,
            "category_filter": category_filter,
            "search": search,
            "category_choices": Note.CATEGORY_CHOICES,
            "total_notes": total_notes,
            "pinned_count": pinned_count,
            "archived_count": archived_count,
        },
    )


@login_required
def note_create(request):
    if request.method == "POST":
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            messages.success(request, "Note saved.")
            return redirect("notes_list")
    else:
        form = NoteForm(
            initial={
                "date": timezone.localdate(),
                "color": "yellow",
                "category": "ideas",
                "priority": "med",
            }
        )

    return render(request, "notes/note_form.html", {"form": form, "action": "Create"})


@login_required
def note_edit(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == "POST":
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, "Note updated.")
            return redirect("notes_list")
    else:
        form = NoteForm(instance=note)

    return render(request, "notes/note_form.html", {"form": form, "note": note, "action": "Edit"})


@login_required
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == "POST":
        note.delete()
        messages.success(request, "Note deleted.")
    return redirect("notes_list")


@login_required
def note_toggle_pin(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == "POST":
        note.is_pinned = not note.is_pinned
        note.save()
        messages.success(request, "Note pinned." if note.is_pinned else "Note unpinned.")
    return redirect("notes_list")


@login_required
def note_archive(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == "POST":
        if note.category == ARCHIVED_CATEGORY:
            note.category = DEFAULT_CATEGORY
            messages.success(request, "Note unarchived.")
        else:
            note.category = ARCHIVED_CATEGORY
            messages.success(request, "Note archived.")
        note.save()
    return redirect("notes_list")
