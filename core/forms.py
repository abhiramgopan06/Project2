from django import forms
from .models import PropertyReport


class PropertyReportForm(forms.ModelForm):
    class Meta:
        model = PropertyReport
        fields = ["reason", "description"]
        widgets = {
            "reason": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Explain the problem clearly..."}),
        }
