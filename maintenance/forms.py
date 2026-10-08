from django import forms
from django.contrib.auth import get_user_model

from .models import MaintenanceTicket, Technician

User = get_user_model()


class MaintenanceTicketForm(forms.ModelForm):
    class Meta:
        model = MaintenanceTicket
        fields = ["property", "room", "title", "description", "priority"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5, "placeholder": "Explain the problem clearly so the technician can prepare before visiting."})}

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        if tenant:
            bookings = tenant.bookings.filter(status="CONFIRMED").select_related("property", "room")
            property_ids = bookings.values_list("property_id", flat=True).distinct()
            self.fields["property"].queryset = self.fields["property"].queryset.filter(id__in=property_ids)
            self.fields["room"].queryset = self.fields["room"].queryset.filter(property_id__in=property_ids)

    def clean(self):
        cleaned = super().clean()
        tenant = self.tenant
        property_obj = cleaned.get("property")
        room = cleaned.get("room")
        if tenant and property_obj:
            booking_qs = tenant.bookings.filter(status="CONFIRMED", property=property_obj).select_related("room")
            if room and not booking_qs.filter(room=room).exists():
                raise forms.ValidationError("You can only create a maintenance request for the room you rented.")
            elif not room and not booking_qs.filter(room__isnull=True).exists() and booking_qs.exists():
                raise forms.ValidationError("Please select the room included in your rental booking.")
        if len((cleaned.get("description") or "").strip()) < 20:
            self.add_error("description", "Please describe the problem clearly using at least 20 characters.")
        return cleaned


class TechnicianForm(forms.ModelForm):
    """Owner-only account creation form. Owners cannot edit credentials later."""
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = Technician
        fields = ["name", "email", "phone", "specialization", "available"]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already taken. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

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


class TechnicianAccountForm(forms.Form):
    """Technician can change only their own login credentials."""
    username = forms.CharField(max_length=150)
    new_password = forms.CharField(widget=forms.PasswordInput, min_length=8, required=False, help_text="Leave blank if you only want to change the username.")
    confirm_password = forms.CharField(widget=forms.PasswordInput, min_length=8, required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            self.fields["username"].initial = user.username

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        qs = User.objects.filter(username__iexact=username)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")
        if password or confirm:
            if not password or not confirm:
                raise forms.ValidationError("Enter the new password in both password fields.")
            if password != confirm:
                raise forms.ValidationError("The passwords do not match.")
        return cleaned


class MaintenanceMessageForm(forms.Form):
    message = forms.CharField(
        min_length=2,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ask a question or add useful clarification..."}),
    )


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
