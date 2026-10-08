from django import forms
from django.utils import timezone

from properties.models import Room
from .models import RentalRequest
from .utils import MAX_RENTAL_MONTHS, MIN_RENTAL_MONTHS


class RentalRequestForm(forms.ModelForm):
    class Meta:
        model = RentalRequest
        fields = ["room", "move_in_date", "duration_months", "message"]
        widgets = {
            "room": forms.Select(attrs={"class": "form-select"}),
            "move_in_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "duration_months": forms.NumberInput(
                attrs={"class": "form-control", "min": MIN_RENTAL_MONTHS, "max": MAX_RENTAL_MONTHS, "step": 1}
            ),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Tell the owner anything important about your rental request..."}),
        }

    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.property_obj = property_obj
        self.fields["duration_months"].help_text = (
            f"How many months do you want to rent for? ({MIN_RENTAL_MONTHS}-{MAX_RENTAL_MONTHS})"
        )
        if property_obj is not None:
                                                                               
                                                                             
                                                                              
                                                                             
                                                                   
            self.instance.property = property_obj
            self.fields["room"].queryset = property_obj.rooms.filter(available=True)
            self.fields["room"].required = False
            self.fields["room"].empty_label = "Entire property / no specific room"

    def clean_move_in_date(self):
        value = self.cleaned_data["move_in_date"]
        if value < timezone.localdate():
            raise forms.ValidationError("Choose today or a future date.")
        return value

    def clean_duration_months(self):
        value = self.cleaned_data["duration_months"]
        if value < MIN_RENTAL_MONTHS or value > MAX_RENTAL_MONTHS:
            raise forms.ValidationError(
                f"Rental duration must be between {MIN_RENTAL_MONTHS} and {MAX_RENTAL_MONTHS} months."
            )
        return value

    def clean_room(self):
        room = self.cleaned_data.get("room")
        if room and self.property_obj and room.property_id != self.property_obj.pk:
            raise forms.ValidationError("Invalid room selected.")
        return room
