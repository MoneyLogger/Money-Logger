from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("savings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="savingtransaction",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="savinggoal",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
