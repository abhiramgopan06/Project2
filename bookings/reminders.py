"""Rent reminders: works out which of a tenant's bookings have rent due soon."""
from django.utils import timezone

from .models import Booking
from .utils import REMINDER_DAYS_BEFORE


def rent_reminders_for(tenant):
    """Return a list of reminders for rent due within the next few days.

    Each reminder is a small dictionary with the booking, the due date,
    how many days are left, and the amount. Nothing is stored in the database.
    """
    today = timezone.localdate()
    bookings = Booking.objects.filter(
        tenant=tenant, status=Booking.Status.CONFIRMED
    ).select_related("property", "room")

    reminders = []
    for booking in bookings:
        due_date = booking.next_rent_due(today)
        if due_date is None:
            continue
        days_left = (due_date - today).days
        if days_left <= REMINDER_DAYS_BEFORE:
            reminders.append(
                {
                    "booking": booking,
                    "due_date": due_date,
                    "days_left": days_left,
                    "amount": booking.monthly_rent(),
                }
            )
    return reminders
