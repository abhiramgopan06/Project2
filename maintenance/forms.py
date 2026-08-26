from django import forms
from django.contrib.auth import get_user_model

from .models import MaintenanceTicket, Technician

User = get_user_model()


class MaintenanceTicketForm(forms.ModelForm):
    class Meta:
        model = MaintenanceTicket
        fields = ["property", "room", "title", "description", "priority"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            bookings = tenant.bookings.filter(status="CONFIRMED").select_related("property", "room")
            property_ids = bookings.values_list("property_id", flat=True).distinct()
            self.fields["property"].queryset = self.fields["property"].queryset.filter(id__in=property_ids)
            self.fields["room"].queryset = self.fields["room"].queryset.filter(property_id__in=property_ids)


class TechnicianForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = Technician
        fields = ["name", "email", "phone", "specialization", "available"]

    def save(self, owner, commit=True):
        technician = super().save(commit=False)
        user = User(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            role=User.Role.TECHNICIAN,
        )
        user.set_password(self.cleaned_data["password"])
        user.save()
        technician.owner = owner
        technician.user = user
        if commit:
            technician.save()
        return technician


class AssignTechnicianForm(forms.ModelForm):
    class Meta:
        model = MaintenanceTicket
        fields = ["technician", "owner_note"]
        widgets = {"owner_note": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["technician"].queryset = Technician.objects.none()
        if owner:
            self.fields["technician"].queryset = Technician.objects.filter(owner=owner, available=True)
