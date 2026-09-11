from django import forms
from django.contrib.auth import get_user_model

from .models import MaintenanceTicket, Technician

User = get_user_model()


class MaintenanceTicketForm(forms.ModelForm):
    """Form a tenant fills in to raise a maintenance request."""

    class Meta:
        model = MaintenanceTicket
        fields = ["property", "room", "title", "description", "priority"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            # A tenant should only be able to raise a ticket for a property
            # (and room) they actually have a confirmed booking for.
            bookings = tenant.bookings.filter(status="CONFIRMED").select_related("property", "room")
            property_ids = bookings.values_list("property_id", flat=True).distinct()
            self.fields["property"].queryset = self.fields["property"].queryset.filter(id__in=property_ids)
            self.fields["room"].queryset = self.fields["room"].queryset.filter(property_id__in=property_ids)


class TechnicianForm(forms.ModelForm):
    """Form an owner fills in to add a new technician.

    Creating a technician also creates a login account for them (with the
    TECHNICIAN role), so this form includes username/password fields on
    top of the normal Technician model fields.
    """

    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = Technician
        fields = ["name", "email", "phone", "specialization", "available"]

    # These two checks stop the page from crashing with a server error when
    # someone tries to create a technician account with a username or email
    # that is already used by another account.
    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already taken. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, owner, commit=True):
        # First build the login account for the technician, then attach a
        # Technician profile to it and link it back to the owner who
        # created it.
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
    """Form an owner uses to assign one of their technicians to a ticket."""

    class Meta:
        model = MaintenanceTicket
        fields = ["technician", "owner_note"]
        widgets = {"owner_note": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show technicians that belong to this owner and are marked
        # as available, so an owner can never assign someone else's
        # technician (or one who is already busy) to a ticket.
        self.fields["technician"].queryset = Technician.objects.none()
        if owner:
            self.fields["technician"].queryset = Technician.objects.filter(owner=owner, available=True)
