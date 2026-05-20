from django.urls import path

from .views import note_archive, note_create, note_delete, note_edit, note_toggle_pin, notes_list


urlpatterns = [
    path("", notes_list, name="notes_list"),
    path("create/", note_create, name="note_create"),
    path("<int:pk>/edit/", note_edit, name="note_edit"),
    path("<int:pk>/delete/", note_delete, name="note_delete"),
    path("<int:pk>/archive/", note_archive, name="note_archive"),
    path("<int:pk>/toggle-pin/", note_toggle_pin, name="note_toggle_pin"),
]
