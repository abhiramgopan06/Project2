from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from properties.models import Property, Room
from .forms import RentalRequestForm
from .models import Booking, RentalRequest


def tenant_required(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('accounts:login')}?next={request.get_full_path()}")
    if request.user.role != "TENANT":
        messages.error(request, "Tenant access is required.")
        return redirect("accounts:dashboard")
    return None


def owner_required(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('accounts:login')}?next={request.get_full_path()}")
    if request.user.role != "OWNER":
        messages.error(request, "Owner access is required.")
        return redirect("accounts:dashboard")
    return None


@login_required
def create_request(request, property_pk):
    blocked = tenant_required(request)
    if blocked:
        return blocked

    property_obj = get_object_or_404(
        Property.objects.prefetch_related("rooms"), pk=property_pk, available=True
    )

    if property_obj.owner_id == request.user.id:
        messages.error(request, "You cannot request your own property.")
        return redirect("properties:detail", pk=property_pk)

    active_request = RentalRequest.objects.filter(
        tenant=request.user,
        property=property_obj,
        status__in=[RentalRequest.Status.PENDING, RentalRequest.Status.APPROVED],
    ).first()
    if active_request:
        messages.info(request, "You already have an active request for this property.")
        return redirect("bookings:my_requests")

    if request.method == "POST":
        form = RentalRequestForm(request.POST, property_obj=property_obj)
        if form.is_valid():
            rental_request = form.save(commit=False)
            rental_request.tenant = request.user
            rental_request.property = property_obj
            rental_request.save()

            send_mail(
                subject=f"New rental request for {property_obj.title}",
                message=(
                    f"{request.user.get_full_name() or request.user.username} has requested "
                    f"your property '{property_obj.title}'. Please review it from your owner dashboard."
                ),
                from_email=None,
                recipient_list=[property_obj.owner.email],
                fail_silently=True,
            )
            messages.success(request, "Rental request submitted successfully.")
            return redirect("bookings:my_requests")
    else:
        form = RentalRequestForm(property_obj=property_obj)

    return render(request, "bookings/request_form.html", {"form": form, "property": property_obj})


@login_required
def my_requests(request):
    blocked = tenant_required(request)
    if blocked:
        return blocked
    requests = RentalRequest.objects.filter(tenant=request.user).select_related("property", "room")
    return render(request, "bookings/my_requests.html", {"requests": requests})


@login_required
def my_bookings(request):
    blocked = tenant_required(request)
    if blocked:
        return blocked
    bookings = Booking.objects.filter(tenant=request.user).select_related("property", "room", "rental_request")
    return render(request, "bookings/my_bookings.html", {"bookings": bookings})


@login_required
def owner_requests(request):
    blocked = owner_required(request)
    if blocked:
        return blocked
    requests = RentalRequest.objects.filter(property__owner=request.user).select_related("tenant", "property", "room")
    return render(request, "bookings/owner_requests.html", {"requests": requests})


@login_required
@transaction.atomic
def approve_request(request, pk):
    blocked = owner_required(request)
    if blocked:
        return blocked
    rental_request = get_object_or_404(
        RentalRequest.objects.select_for_update().select_related("tenant", "property", "room"),
        pk=pk,
        property__owner=request.user,
    )
    if request.method != "POST":
        return redirect("bookings:owner_requests")
    if rental_request.status != RentalRequest.Status.PENDING:
        messages.warning(request, "Only pending requests can be approved.")
        return redirect("bookings:owner_requests")
    if not rental_request.property.available:
        messages.error(request, "This property is currently unavailable.")
        return redirect("bookings:owner_requests")
    if rental_request.room and not rental_request.room.available:
        messages.error(request, "The selected room is no longer available.")
        return redirect("bookings:owner_requests")

    conflicting = Booking.objects.filter(
        property=rental_request.property,
        status=Booking.Status.CONFIRMED,
        start_date__gte=rental_request.move_in_date,
    )
    if rental_request.room:
        conflicting = conflicting.filter(room=rental_request.room)
    elif conflicting.exists():
        messages.error(request, "This property already has a confirmed booking from the requested date.")
        return redirect("bookings:owner_requests")

    rental_request.status = RentalRequest.Status.APPROVED
    rental_request.save(update_fields=["status", "updated_at"])

    booking = Booking.objects.create(
        rental_request=rental_request,
        tenant=rental_request.tenant,
        property=rental_request.property,
        room=rental_request.room,
        start_date=rental_request.move_in_date,
    )

    if rental_request.room:
        rental_request.room.available = False
        rental_request.room.save(update_fields=["available"])
    else:
        rental_request.property.available = False
        rental_request.property.save(update_fields=["available"])

    send_mail(
        subject=f"Rental request approved - {rental_request.property.title}",
        message=(
            f"Your rental request for '{rental_request.property.title}' has been approved. "
            f"Booking #{booking.pk} starts on {booking.start_date}."
        ),
        from_email=None,
        recipient_list=[rental_request.tenant.email],
        fail_silently=True,
    )
    messages.success(request, f"Request #{rental_request.pk} approved and booking #{booking.pk} created.")
    return redirect("bookings:owner_requests")


@login_required
@transaction.atomic
def reject_request(request, pk):
    blocked = owner_required(request)
    if blocked:
        return blocked
    rental_request = get_object_or_404(RentalRequest, pk=pk, property__owner=request.user)
    if request.method != "POST":
        return redirect("bookings:owner_requests")
    if rental_request.status != RentalRequest.Status.PENDING:
        messages.warning(request, "Only pending requests can be rejected.")
        return redirect("bookings:owner_requests")

    rental_request.status = RentalRequest.Status.REJECTED
    rental_request.save(update_fields=["status", "updated_at"])
    send_mail(
        subject=f"Rental request rejected - {rental_request.property.title}",
        message=f"Your rental request for '{rental_request.property.title}' was rejected by the owner.",
        from_email=None,
        recipient_list=[rental_request.tenant.email],
        fail_silently=True,
    )
    messages.success(request, "Rental request rejected.")
    return redirect("bookings:owner_requests")
