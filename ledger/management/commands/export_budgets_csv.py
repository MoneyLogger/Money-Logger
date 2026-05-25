import csv
from django.core.management.base import BaseCommand
from ledger.models import Budget


class Command(BaseCommand):
    help = "Export budgets"

    def handle(self, *args, **kwargs):

        with open("budgets.csv", "w", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)

            writer.writerow([
                "id",
                "user",
                "category",
                "amount",
                "period",
                "month",
                "year",
                "alert_threshold",
                "created_at",
            ])

            for b in Budget.objects.select_related("user"):

                writer.writerow([
                    b.id,
                    b.user.username,
                    b.category,
                    b.amount,
                    b.period,
                    b.month,
                    b.year,
                    b.alert_threshold,
                    b.created_at,
                ])

        self.stdout.write(self.style.SUCCESS("Budgets exported!"))