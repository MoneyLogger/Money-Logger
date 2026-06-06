from django.urls import path

from .views import dashboard, analytics, survival_dashboard, budget_list, budget_create, budget_edit, budget_delete, budget_update_ajax, budget_delete_ajax, trash_view, export_data

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("analytics/", analytics, name="analytics"),
    path("survival/", survival_dashboard, name="survival"),
    path("budget/", budget_list, name="budget_list"),
    path("budget/create/", budget_create, name="budget_create"),
    path("budget/<int:budget_id>/edit/", budget_edit, name="budget_edit"),
    path("budget/<int:budget_id>/delete/", budget_delete, name="budget_delete"),
    path("budget/update-ajax/", budget_update_ajax, name="budget_update_ajax"),
    path("budget/delete-ajax/", budget_delete_ajax, name="budget_delete_ajax"),
    path("trash/", trash_view, name="trash_view"),
    path("export/", export_data, name="export_data"),
]
