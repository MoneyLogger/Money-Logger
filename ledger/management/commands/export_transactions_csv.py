import csv
from django.core.management.base import BaseCommand
from ledger.models import Transaction


class Command(BaseCommand):
    help = "Export transactions to CSV"

    def handle(self, *args, **kwargs):

        with open("transactions.csv", "w", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)

            writer.writerow([
                "id",
                "user",
                "transaction_type",
                "money_type",
                "switch_direction",
                "amount",
                "category",
                "description",
                "date",
                "created_at",
            ])

            for t in Transaction.objects.select_related("user"):

                writer.writerow([
                    t.id,
                    t.user.username,
                    t.transaction_type,
                    t.money_type,
                    t.switch_direction,
                    t.amount,
                    t.category,
                    t.description,
                    t.date,
                    t.created_at,
                ])

        self.stdout.write(self.style.SUCCESS("Transactions exported!"))