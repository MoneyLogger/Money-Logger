import datetime
from django import forms
from .models import Transaction, Budget

CATEGORY_CHOICES = [
    ('Food', 'Food'),
    ('Snacks', 'Snacks'),
    ('Salary', 'Salary'),
    ('Family', 'Family'),
    ('Friend', 'Friend'),
    ('Rent', 'Rent'),
    ('Travels', 'Travels'),
    ('Home Things', 'Home Things'),
    ('Loan', 'Loan'),
    ('Purchasing', 'Purchasing'),
    ('Cashback', 'Cashback'),
    ('Others', 'Others'),
]

MONEY_TYPE_CHOICES = [
    ('HAND CASH', 'Hand Cash'),
    ('UPI CASH', 'UPI Cash'),
]

class TransactionForm(forms.ModelForm):
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control form-textarea", "rows": 2, "placeholder": "Optional description"}))
    
    def __init__(self, *args, **kwargs):
        kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Always show the full category list for all users
        self.fields['category'].choices = CATEGORY_CHOICES

        # Ensure all fields have proper CSS classes
        self.fields['category'].widget.attrs.update({"class": "form-control form-select"})
        self.fields['money_type'].widget.attrs.update({"class": "form-control form-select"})
        self.fields['switch_direction'].required = False
    
    category = forms.ChoiceField(choices=CATEGORY_CHOICES, widget=forms.Select(attrs={"class": "form-control form-select"}))
    money_type = forms.ChoiceField(choices=MONEY_TYPE_CHOICES, widget=forms.Select(attrs={"class": "form-control form-select"}))
    
    class Meta:
        model = Transaction
        fields = [
            "transaction_type",
            "money_type",
            "switch_direction",
            "amount",
            "category",
            "description",
            "date",
        ]

        widgets = {
            "transaction_type": forms.Select(attrs={"class": "form-control form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control form-input", "step": "0.01"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control form-input"}),
        }

class SwitchForm(forms.ModelForm):
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control form-textarea", "rows": 2, "placeholder": "Optional note (e.g., ATM withdrawal, bank deposit)"}))
    
    class Meta:
        model = Transaction
        fields = ["amount", "switch_direction", "description", "date"]
        widgets = {
            "amount": forms.NumberInput(attrs={"class": "form-control form-input", "step": "0.01", "placeholder": "Enter amount"}),
            "switch_direction": forms.Select(attrs={"class": "form-control form-select"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control form-input"}),
        }


class BudgetForm(forms.ModelForm):
    category = forms.ChoiceField(choices=CATEGORY_CHOICES, widget=forms.Select(attrs={"class": "form-control form-select"}))
    
    def __init__(self, *args, **kwargs):
        kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Always show the full category list for all users
        self.fields['category'].choices = CATEGORY_CHOICES

        # Default month and year to current date (only for new forms, not edits)
        if not self.instance.pk:
            today = datetime.date.today()
            self.fields['month'].initial = today.month
            self.fields['year'].initial = today.year

        # Always ensure category field has proper CSS class
        self.fields['category'].widget.attrs.update({"class": "form-control form-select"})
    
    class Meta:
        model = Budget
        fields = ["category", "amount", "period", "month", "year", "alert_threshold"]
        widgets = {
            "amount": forms.NumberInput(attrs={
                "class": "form-control form-input",
                "step": "0.01",
                "placeholder": "Enter budget amount"
            }),
            "period": forms.Select(attrs={"class": "form-control form-select"}),
            "month": forms.Select(attrs={"class": "form-control form-select"}, choices=[
                (1, "January"), (2, "February"), (3, "March"), (4, "April"),
                (5, "May"), (6, "June"), (7, "July"), (8, "August"),
                (9, "September"), (10, "October"), (11, "November"), (12, "December")
            ]),
            "year": forms.NumberInput(attrs={"class": "form-control form-input"}),
            "alert_threshold": forms.NumberInput(attrs={
                "class": "form-control form-input",
                "min": "0",
                "max": "100",
                "placeholder": "Alert at % (default: 80)"
            }),
        }
