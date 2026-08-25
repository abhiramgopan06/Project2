from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Amenities"

    def __str__(self):
        return self.name


class Property(models.Model):
    class PropertyType(models.TextChoices):
        APARTMENT = "APARTMENT", "Apartment"
        HOUSE = "HOUSE", "House"
        VILLA = "VILLA", "Villa"
        STUDIO = "STUDIO", "Studio"
        PG = "PG", "PG / Shared Accommodation"
        OFFICE = "OFFICE", "Office"
        OTHER = "OTHER", "Other"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="properties",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    location = models.CharField(max_length=150, db_index=True)
    address = models.TextField()
    number_of_rooms = models.PositiveIntegerField(default=1)
    rent = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    available = models.BooleanField(default=True, db_index=True)
    amenities = models.ManyToManyField(Amenity, blank=True, related_name="properties")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="properties/%Y/%m/")
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "-uploaded_at"]

    def save(self, *args, **kwargs):
        if self.is_primary:
            PropertyImage.objects.filter(property=self.property, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        elif not PropertyImage.objects.filter(property=self.property).exclude(pk=self.pk).exists():
            self.is_primary = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.property.title}"


class Room(models.Model):
    class RoomType(models.TextChoices):
        SINGLE = "SINGLE", "Single"
        DOUBLE = "DOUBLE", "Double"
        SHARED = "SHARED", "Shared"
        MASTER = "MASTER", "Master"
        OTHER = "OTHER", "Other"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=50)
    room_type = models.CharField(max_length=20, choices=RoomType.choices, default=RoomType.SINGLE)
    rent = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    available = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["room_number"]
        constraints = [
            models.UniqueConstraint(fields=["property", "room_number"], name="unique_room_number_per_property")
        ]

    def __str__(self):
        return f"{self.property.title} - Room {self.room_number}"
