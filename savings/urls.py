from django.urls import path
from . import views

urlpatterns = [
    path("", views.saving_dashboard, name="saving_dashboard"),
    path("create/", views.create_goal, name="create_goal"),
    path("<int:pk>/", views.goal_detail, name="goal_detail"),
    path("<int:pk>/add/", views.add_saving, name="add_saving"),
    path("<int:pk>/withdraw/", views.withdraw_saving, name="withdraw_saving"),
    path("<int:pk>/edit/", views.edit_goal, name="edit_goal"),
    path("<int:pk>/delete/", views.delete_goal, name="delete_goal"),
    path("analytics/", views.saving_analytics, name="saving_analytics"),
]
