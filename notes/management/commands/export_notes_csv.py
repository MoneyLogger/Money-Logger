import csv
from django.core.management.base import BaseCommand
from notes.models import Note


class Command(BaseCommand):
    help = "Export notes"

    def handle(self, *args, **kwargs):

        with open("notes.csv", "w", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)

            writer.writerow([
                "id",
                "user",
                "title",
                "content",
                "color",
                "category",
                "priority",
                "is_pinned",
                "date",
                "created_at",
            ])

            for n in Note.objects.select_related("user"):

                writer.writerow([
                    n.id,
                    n.user.username,
                    n.title,
                    n.content,
                    n.color,
                    n.category,
                    n.priority,
                    n.is_pinned,
                    n.date,
                    n.created_at,
                ])

        self.stdout.write(self.style.SUCCESS("Notes exported!"))