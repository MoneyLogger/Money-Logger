import csv
from django.core.management.base import BaseCommand
from ledger.models import ActivityLog


class Command(BaseCommand):
    help = "Export activity logs"

    def handle(self, *args, **kwargs):

        with open("activity_logs.csv", "w", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)

            writer.writerow([
                "id",
                "user",
                "action",
                "transaction_type",
                "amount",
                "category",
                "description",
                "date",
                "money_type",
                "changes",
                "timestamp",
            ])

            for log in ActivityLog.objects.select_related("user"):

                writer.writerow([
                    log.id,
                    log.user.username,
                    log.action,
                    log.transaction_type,
                    log.amount,
                    log.category,
                    log.description,
                    log.date,
                    log.money_type,
                    log.changes,
                    log.timestamp,
                ])

        self.stdout.write(self.style.SUCCESS("Activity logs exported!"))