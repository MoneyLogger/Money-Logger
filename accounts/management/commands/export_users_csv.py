import csv
from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "Export users to CSV"

    def handle(self, *args, **kwargs):

        with open("users.csv", "w", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)

            writer.writerow([
                "id",
                "username",
                "email",
                "first_name",
                "last_name",
                "is_staff",
                "date_joined",
            ])

            for user in User.objects.all():

                writer.writerow([
                    user.id,
                    user.username,
                    user.email,
                    user.first_name,
                    user.last_name,
                    user.is_staff,
                    user.date_joined,
                ])

        self.stdout.write(self.style.SUCCESS("Users exported!"))