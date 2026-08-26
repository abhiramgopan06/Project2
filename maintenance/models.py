from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from bookings.models import Booking
from properties.models import Property, Room


class Technician(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="technicians",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="technician_profile",
    )
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MaintenanceTicket(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        EMERGENCY = "EMERGENCY", "Emergency"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="maintenance_tickets")
    property = models.ForeignKey(Property, on_delete=models.PROTECT, related_name="maintenance_tickets")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_tickets")
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="maintenance_tickets")
    technician = models.ForeignKey(Technician, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets")
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN, db_index=True)
    owner_note = models.TextField(blank=True)
    technician_note = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        if self.booking_id:
            if self.booking.tenant_id != self.tenant_id:
                raise ValidationError("The booking does not belong to this tenant.")
            if self.booking.property_id != self.property_id:
                raise ValidationError("The booking does not belong to this property.")
            if self.booking.status != Booking.Status.CONFIRMED:
                raise ValidationError("Maintenance requests require a confirmed booking.")
        if self.room_id and self.room.property_id != self.property_id:
            raise ValidationError("The selected room does not belong to this property.")
        if self.technician_id and self.technician.owner_id != self.property.owner_id:
            raise ValidationError("The technician must belong to the property owner.")

    def mark_resolved(self):
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at", "updated_at"])

    def mark_closed(self):
        self.status = self.Status.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=["status", "closed_at", "updated_at"])

    def __str__(self):
        return f"Ticket #{self.pk} - {self.title}"
