from django.contrib import admin
from .models import SavingGoal, SavingTransaction


@admin.register(SavingGoal)
class SavingGoalAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "icon", "target_amount", "current_amount", "status", "deadline", "created_at", "is_active"]
    list_filter = ["status", "deadline", "is_active"]
    search_fields = ["title", "description"]
    ordering = ["-created_at"]

    def get_queryset(self, request):
        return SavingGoal.all_objects.all()


@admin.register(SavingTransaction)
class SavingTransactionAdmin(admin.ModelAdmin):
    list_display = ["user", "saving_goal", "transaction_type", "source", "amount", "date", "created_at", "is_active"]
    list_filter = ["transaction_type", "source", "date", "is_active"]
    search_fields = ["note"]
    ordering = ["-created_at"]

    def get_queryset(self, request):
        return SavingTransaction.all_objects.all()
