from django.contrib import admin
from .models import SavingGoal, SavingTransaction


@admin.register(SavingGoal)
class SavingGoalAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "icon", "target_amount", "current_amount", "status", "deadline", "created_at"]
    list_filter = ["status", "deadline"]
    search_fields = ["title", "description"]
    ordering = ["-created_at"]


@admin.register(SavingTransaction)
class SavingTransactionAdmin(admin.ModelAdmin):
    list_display = ["user", "saving_goal", "transaction_type", "source", "amount", "date", "created_at"]
    list_filter = ["transaction_type", "source", "date"]
    search_fields = ["note"]
    ordering = ["-created_at"]
