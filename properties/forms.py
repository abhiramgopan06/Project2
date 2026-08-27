from django import forms

from .models import Amenity, Property, PropertyImage, Room


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            "title",
            "description",
            "property_type",
            "location",
            "address",
            "number_of_rooms",
            "rent",
            "available",
            "amenities",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "address": forms.Textarea(attrs={"rows": 3}),
            "amenities": forms.CheckboxSelectMultiple(),
            "rent": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amenities"].queryset = Amenity.objects.all()


    def clean(self):
        cleaned = super().clean()
        rooms = cleaned.get("number_of_rooms")
        rent = cleaned.get("rent")
        if rooms is not None and rooms < 1:
            self.add_error("number_of_rooms", "A property must have at least one room.")
        if rent is not None and rent < 0:
            self.add_error("rent", "Rent cannot be negative.")
        return cleaned


class PropertyImageForm(forms.ModelForm):
    class Meta:
        model = PropertyImage
        fields = ["image", "caption", "is_primary"]
        widgets = {"image": forms.ClearableFileInput(attrs={"accept": "image/*"})}


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["room_number", "room_type", "rent", "available", "description"]
        widgets = {
            "rent": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }
