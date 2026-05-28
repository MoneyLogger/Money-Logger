from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ledger", "0007_remove_note_user_alter_budget_unique_together_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="budget",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddConstraint(
            model_name="budget",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_active", True)),
                fields=("user", "category", "month", "year", "period"),
                name="unique_active_budget",
            ),
        ),
    ]
