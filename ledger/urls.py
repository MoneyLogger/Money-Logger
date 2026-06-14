from django.urls import path
from .views import (
    add_transaction, switch_money, edit_transaction, edit_saving_transaction,
    delete_transaction, toggle_pin, activity_log, toggle_whatif, confirm_whatif_transaction,
    edit_whatif_transaction, export_transactions,
)

urlpatterns = [
    path("add/", add_transaction, name="add_transaction"),
    path("export/", export_transactions, name="export_transactions"),
    path("switch/", switch_money, name="switch_money"),
    path("<int:pk>/edit/", edit_transaction, name="edit_transaction"),
    path("<int:pk>/edit-saving/", edit_saving_transaction, name="edit_saving_transaction"),
    path("<int:pk>/delete/", delete_transaction, name="delete_transaction"),
    path("<int:pk>/toggle-pin/", toggle_pin, name="toggle_transaction_pin"),
    path("activity-log/", activity_log, name="activity_log"),
    path("whatif/toggle/", toggle_whatif, name="toggle_whatif"),
    path("whatif/<int:pk>/confirm/", confirm_whatif_transaction, name="confirm_whatif_transaction"),
    path("whatif/<int:pk>/edit/", edit_whatif_transaction, name="edit_whatif_transaction"),
]
