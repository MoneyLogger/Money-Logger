import csv
from django.core.management.base import BaseCommand
from savings.models import SavingGoal


class Command(BaseCommand):
    help = "Export saving goals"

    def handle(self, *args, **kwargs):

        with open("saving_goals.csv", "w", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)

            writer.writerow([
                "id",
                "user",
                "title",
                "target_amount",
                "current_amount",
                "status",
                "deadline",
                "created_at",
            ])

            for s in SavingGoal.objects.select_related("user"):

                writer.writerow([
                    s.id,
                    s.user.username,
                    s.title,
                    s.target_amount,
                    s.current_amount,
                    s.status,
                    s.deadline,
                    s.created_at,
                ])

        self.stdout.write(self.style.SUCCESS("Saving goals exported!"))