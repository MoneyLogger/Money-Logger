from django.conf import settings
from django.db import models


class ActiveManager(models.Manager):
    """Only returns active (non-soft-deleted) records."""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Transaction(models.Model):
    TRANSACTION_TYPE = (
        ("INCOME", "Income"),
        ("EXPENSE", "Expense"),
        ("SWITCH", "Switch"),
        ("SAVING", "Saving"),
    )

    MONEY_TYPE = (
        ("HAND CASH", "Hand Cash"),
        ("UPI CASH", "UPI Cash")
    )

    SWITCH_DIRECTION = (
        ("UPI_TO_HAND", "UPI to Hand"),
        ("HAND_TO_UPI", "Hand to UPI"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)
    money_type = models.CharField(max_length=20, choices=MONEY_TYPE, default="HAND CASH")
    switch_direction = models.CharField(max_length=20, choices=SWITCH_DIRECTION, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        indexes = [
            models.Index(fields=["user", "date"], name="tx_user_date_idx"),
            models.Index(fields=["user", "transaction_type", "money_type"], name="tx_type_money_idx"),
            models.Index(fields=["user", "is_active"], name="tx_active_idx"),
            models.Index(fields=["user", "is_pinned"], name="tx_pinned_idx"),
            models.Index(fields=["user", "category", "transaction_type", "date"], name="tx_budget_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} - ₹{self.amount}"


class ActivityLog(models.Model):
    ACTION_CHOICES = (
        ("EDIT", "Edited"),
        ("DELETE", "Deleted"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activity_logs"
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    transaction_type = models.CharField(max_length=10, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=200, blank=True)
    date = models.DateField()
    money_type = models.CharField(max_length=20, blank=True)
    # For edits: store what changed
    changes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"], name="al_user_ts_idx"),
            models.Index(fields=["user", "action"], name="al_action_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} {self.action} ₹{self.amount} on {self.timestamp:%d %b %Y %H:%M}"


class WhatIfTransaction(models.Model):
    """Temporary transactions for What-If mode simulation"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="whatif_transactions"
    )
    transaction_type = models.CharField(max_length=10, choices=Transaction.TRANSACTION_TYPE)
    money_type = models.CharField(max_length=20, choices=Transaction.MONEY_TYPE, default="HAND CASH")
    switch_direction = models.CharField(max_length=20, choices=Transaction.SWITCH_DIRECTION, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "date"], name="wi_user_date_idx"),
            models.Index(fields=["user", "transaction_type"], name="wi_type_idx"),
        ]

    def __str__(self):
        return f"[WHAT-IF] {self.user.username} - ₹{self.amount}"


class Budget(models.Model):
    """Monthly budget for different categories"""
    PERIOD_CHOICES = (
        ("MONTHLY", "Monthly"),
        ("YEARLY", "Yearly"),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgets"
    )
    category = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default="MONTHLY")
    month = models.IntegerField(default=1)  # 1-12 for monthly budgets
    year = models.IntegerField()
    alert_threshold = models.IntegerField(default=80)  # Alert when 80% spent
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-year", "-month", "category"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "month", "year", "period"],
                condition=models.Q(is_active=True),
                name="unique_active_budget"
            )
        ]
        indexes = [
            models.Index(fields=["user", "is_active"], name="budget_active_idx"),
            models.Index(fields=["user", "month", "year"], name="budget_period_idx"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.category}: ₹{self.amount} ({self.period})"

    def get_spent_amount(self):
        """Calculate net spent in this budget period (expenses minus income)"""
        from django.db.models import Sum
        
        expenses = Transaction.objects.filter(
            user=self.user,
            category=self.category,
            transaction_type="EXPENSE",
            date__year=self.year,
            date__month=self.month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        income = Transaction.objects.filter(
            user=self.user,
            category=self.category,
            transaction_type="INCOME",
            date__year=self.year,
            date__month=self.month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return max(0, float(expenses) - float(income))
    
    def get_remaining_amount(self):
        """Calculate remaining budget"""
        return float(self.amount) - self.get_spent_amount()
    
    def get_percentage_used(self):
        """Calculate percentage of budget used"""
        if float(self.amount) == 0:
            return 0
        return (self.get_spent_amount() / float(self.amount)) * 100
    
    def is_over_budget(self):
        """Check if budget is exceeded"""
        return self.get_spent_amount() > float(self.amount)
    
    def is_near_limit(self):
        """Check if spending is near the alert threshold"""
        return self.get_percentage_used() >= self.alert_threshold


