import csv
from django.core.management.base import BaseCommand
from savings.models import SavingTransaction


class Command(BaseCommand):
    help = "Export saving transactions"

    def handle(self, *args, **kwargs):

        with open("saving_transactions.csv", "w", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)

            writer.writerow([
                "id",
                "user",
                "saving_goal",
                "transaction_type",
                "source",
                "amount",
                "note",
                "date",
                "created_at",
            ])

            for s in SavingTransaction.objects.select_related("user", "saving_goal"):

                writer.writerow([
                    s.id,
                    s.user.username,
                    s.saving_goal.title,
                    s.transaction_type,
                    s.source,
                    s.amount,
                    s.note,
                    s.date,
                    s.created_at,
                ])

        self.stdout.write(self.style.SUCCESS("Saving transactions exported!"))