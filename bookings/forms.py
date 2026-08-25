from django import forms
from django.utils import timezone

from properties.models import Room
from .models import RentalRequest


class RentalRequestForm(forms.ModelForm):
    class Meta:
        model = RentalRequest
        fields = ["room", "move_in_date", "message"]
        widgets = {
            "room": forms.Select(attrs={"class": "form-select"}),
            "move_in_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Tell the owner anything important about your rental request..."}),
        }

    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.property_obj = property_obj
        if property_obj is not None:
            self.fields["room"].queryset = property_obj.rooms.filter(available=True)
            self.fields["room"].required = False
            self.fields["room"].empty_label = "Entire property / no specific room"

    def clean_move_in_date(self):
        value = self.cleaned_data["move_in_date"]
        if value < timezone.localdate():
            raise forms.ValidationError("Choose today or a future date.")
        return value

    def clean_room(self):
        room = self.cleaned_data.get("room")
        if room and self.property_obj and room.property_id != self.property_obj.pk:
            raise forms.ValidationError("Invalid room selected.")
        return room
