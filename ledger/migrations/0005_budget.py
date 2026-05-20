# Generated manually for Budget model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ledger', '0004_transaction_switch_direction_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Budget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(max_length=50)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('period', models.CharField(choices=[('MONTHLY', 'Monthly'), ('YEARLY', 'Yearly')], default='MONTHLY', max_length=10)),
                ('month', models.IntegerField(default=1)),
                ('year', models.IntegerField()),
                ('alert_threshold', models.IntegerField(default=80)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budgets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-year', '-month', 'category'],
                'unique_together': {('user', 'category', 'month', 'year', 'period')},
            },
        ),
    ]
