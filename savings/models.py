from django.db import models
from django.conf import settings


class SavingGoal(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
        ("PAUSED", "Paused"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saving_goals",
    )
    title = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default="💰")
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def progress_percentage(self):
        if self.target_amount == 0:
            return 0
        return round((self.current_amount / self.target_amount) * 100, 2)

    def remaining_amount(self):
        return self.target_amount - self.current_amount

    def is_completed(self):
        return self.current_amount >= self.target_amount

    def save(self, *args, **kwargs):
        if self.current_amount >= self.target_amount and self.status != "COMPLETED":
            self.status = "COMPLETED"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.user})"


class SavingTransaction(models.Model):
    SOURCE_CHOICES = [
        ("UPI CASH", "UPI CASH"),
        ("HAND CASH", "HAND CASH"),
    ]
    TYPE_CHOICES = [
        ("ADD", "ADD"),
        ("WITHDRAW", "WITHDRAW"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    saving_goal = models.ForeignKey(
        SavingGoal,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField()

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.user} - {self.amount}"
