from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from properties.models import Property, Room
from .utils import MAX_RENTAL_MONTHS, MIN_RENTAL_MONTHS, format_duration, lease_end_date, next_rent_due_date


class RentalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rental_requests")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="rental_requests")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name="rental_requests")
    move_in_date = models.DateField()
    duration_months = models.PositiveSmallIntegerField(
        "Rental duration (months)",
        default=MIN_RENTAL_MONTHS,
        validators=[MinValueValidator(MIN_RENTAL_MONTHS), MaxValueValidator(MAX_RENTAL_MONTHS)],
    )
    message = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    owner_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        if self.tenant_id and self.property_id and self.property.owner_id == self.tenant_id:
            raise ValidationError("A property owner cannot request their own property.")
        if self.room_id and self.room.property_id != self.property_id:
            raise ValidationError("The selected room does not belong to this property.")
        if self.move_in_date and self.move_in_date < timezone.localdate():
            raise ValidationError("Move-in date cannot be in the past.")

    # These are normal methods (not @property) on purpose: this model has a
    # field called "property", which hides Python's own @property inside the
    # class. Templates can still write {{ item.end_date }} - they call it for you.
    def end_date(self):
        return lease_end_date(self.move_in_date, self.duration_months)

    def duration_display(self):
        return format_duration(self.duration_months)

    def __str__(self):
        return f"Request #{self.pk} - {self.tenant.username} - {self.property.title}"


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    rental_request = models.OneToOneField(RentalRequest, on_delete=models.PROTECT, related_name="booking")
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    property = models.ForeignKey(Property, on_delete=models.PROTECT, related_name="bookings")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, null=True, blank=True, related_name="bookings")
    start_date = models.DateField()
    duration_months = models.PositiveSmallIntegerField(
        "Rental duration (months)",
        default=MIN_RENTAL_MONTHS,
        validators=[MinValueValidator(MIN_RENTAL_MONTHS), MaxValueValidator(MAX_RENTAL_MONTHS)],
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CONFIRMED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    # Normal methods, not @property - see the note in RentalRequest above.
    def end_date(self):
        return lease_end_date(self.start_date, self.duration_months)

    def duration_display(self):
        return format_duration(self.duration_months)

    def next_rent_due(self, today=None):
        """Next date rent is due for this booking (None once the stay is over)."""
        return next_rent_due_date(self.start_date, self.duration_months, today or timezone.localdate())

    def monthly_rent(self):
        return self.room.rent if self.room else self.property.rent

    def __str__(self):
        return f"Booking #{self.pk} - {self.property.title}"
