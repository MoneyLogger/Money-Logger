from django.contrib import admin
from .models import Transaction, ActivityLog, WhatIfTransaction, Budget

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'money_type', 'switch_direction', 'amount', 'category', 'description', 'date', 'created_at', 'is_active']
    list_filter = ['transaction_type', 'money_type', 'switch_direction', 'category', 'date', 'created_at', 'is_active']
    search_fields = ['description', 'category']
    date_hierarchy = 'date'
    ordering = ['-date']

    def get_queryset(self, request):
        return Transaction.all_objects.all()

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'transaction_type', 'amount', 'category', 'date', 'timestamp']
    list_filter = ['action', 'transaction_type', 'timestamp']
    search_fields = ['category', 'description', 'changes']
    ordering = ['-timestamp']

@admin.register(WhatIfTransaction)
class WhatIfTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'money_type', 'amount', 'category', 'date', 'created_at']
    list_filter = ['transaction_type', 'money_type']
    ordering = ['-created_at']

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'amount', 'period', 'month', 'year', 'alert_threshold', 'created_at', 'is_active']
    list_filter = ['period', 'year', 'month', 'category', 'is_active']
    search_fields = ['category']
    ordering = ['-year', '-month', 'category']

    def get_queryset(self, request):
        return Budget.all_objects.all()
