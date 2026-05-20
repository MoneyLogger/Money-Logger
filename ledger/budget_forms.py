from django import forms
from .models import Budget
from datetime import datetime


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount', 'period', 'month', 'year', 'alert_threshold']
        widgets = {
            'category': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Food, Transport, Entertainment'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'period': forms.Select(attrs={'class': 'form-select'}),
            'month': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '2020',
                'max': '2100'
            }),
            'alert_threshold': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'max': '100',
                'value': '80'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default year to current year
        if not self.instance.pk:
            self.fields['year'].initial = datetime.now().year
            self.fields['month'].initial = datetime.now().month
        
        # Month choices
        self.fields['month'].widget.choices = [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]
