from django import forms
from pathlib import Path

from .models import Amenity, Property, PropertyImage, PropertyVerificationDocument, Room


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            "title",
            "description",
            "property_type",
            "location",
            "address",
            "latitude",
            "longitude",
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
            "latitude": forms.NumberInput(
                attrs={"class": "form-control", "step": "any", "min": "-90", "max": "90", "placeholder": "e.g. 12.971600"}
            ),
            "longitude": forms.NumberInput(
                attrs={"class": "form-control", "step": "any", "min": "-180", "max": "180", "placeholder": "e.g. 77.594600"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amenities"].queryset = Amenity.objects.all()


    def clean(self):
        cleaned = super().clean()
        rooms = cleaned.get("number_of_rooms")
        rent = cleaned.get("rent")
        latitude = cleaned.get("latitude")
        longitude = cleaned.get("longitude")
        if rooms is not None and rooms < 1:
            self.add_error("number_of_rooms", "A property must have at least one room.")
        if rent is not None and rent < 0:
            self.add_error("rent", "Rent cannot be negative.")
        if (latitude is None) != (longitude is None):
            self.add_error("latitude", "Provide both latitude and longitude, or leave both blank.")
            self.add_error("longitude", "Provide both latitude and longitude, or leave both blank.")
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


class PropertyVerificationDocumentForm(forms.ModelForm):
    def clean_document(self):
        document = self.cleaned_data["document"]
        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
        if Path(document.name).suffix.lower() not in allowed_extensions:
            raise forms.ValidationError("Upload a PDF, JPG, JPEG or PNG document.")
        if document.size > 8 * 1024 * 1024:
            raise forms.ValidationError("The document must be smaller than 8 MB.")
        return document

    class Meta:
        model = PropertyVerificationDocument
        fields = ["document", "description"]
        widgets = {
            "document": forms.ClearableFileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png"}),
            "description": forms.TextInput(attrs={"placeholder": "e.g. Ownership proof or authorisation"}),
        }
