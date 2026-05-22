from django import forms
from .models import SavingGoal, SavingTransaction


class CreateGoalForm(forms.ModelForm):
    class Meta:
        model = SavingGoal
        fields = ["title", "icon", "target_amount", "description", "deadline"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g., New Laptop"}),
            "icon": forms.TextInput(attrs={"class": "form-input", "placeholder": "💰"}),
            "target_amount": forms.NumberInput(attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}),
            "description": forms.Textarea(attrs={"class": "form-input", "placeholder": "Optional description...", "rows": 3}),
            "deadline": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
        }


class AddSavingForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}),
    )
    source = forms.ChoiceField(
        choices=SavingTransaction.SOURCE_CHOICES,
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    note = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Optional note..."}),
    )


class WithdrawForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}),
    )
    note = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Reason for withdrawal..."}),
    )
