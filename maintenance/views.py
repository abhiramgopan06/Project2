from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from bookings.models import Booking

from .forms import (
    AssignTechnicianForm,
    MaintenanceMessageForm,
    MaintenanceTicketForm,
    TechnicianAccountForm,
    TechnicianForm,
)
from .models import MaintenanceMessage, MaintenanceTicket, Notification, Technician


def _email(subject, message, recipient):
    if recipient:
        send_mail(subject, message, None, [recipient], fail_silently=True)


def _notify(user, title, message, link=""):
    if user:
        Notification.objects.create(recipient=user, title=title, message=message, link=link)
        _email(title, message, user.email)


@login_required
def tenant_tickets(request):
    if request.user.role != "TENANT":
        messages.error(request, "Only tenants can access maintenance requests.")
        return redirect("accounts:dashboard")
    tickets = MaintenanceTicket.objects.filter(tenant=request.user).select_related("property", "room", "technician")
    return render(request, "maintenance/tenant_tickets.html", {"tickets": tickets})


@login_required
def create_ticket(request):
    if request.user.role != "TENANT":
        messages.error(request, "Only tenants can create maintenance requests.")
        return redirect("accounts:dashboard")
    confirmed = Booking.objects.filter(tenant=request.user, status=Booking.Status.CONFIRMED).select_related("property", "room")
    if not confirmed.exists():
        messages.warning(request, "You need a confirmed booking before creating a maintenance request.")
        return redirect("maintenance:tenant_tickets")
    form = MaintenanceTicketForm(request.POST or None, tenant=request.user)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.tenant = request.user
        booking = confirmed.filter(property=ticket.property, room=ticket.room).first() or confirmed.filter(property=ticket.property).first()
        if not booking:
            form.add_error("property", "You do not have a confirmed booking for this property/room.")
        else:
            ticket.booking = booking
            ticket.save()
            owner = ticket.property.owner
            _notify(owner, "New maintenance request", f"{request.user.get_full_name() or request.user.username} reported: {ticket.title} for {ticket.property.title}.", reverse("maintenance:owner_tickets"))
            messages.success(request, "Maintenance request created. Please describe the issue clearly so the technician can prepare.")
            return redirect("maintenance:ticket_detail", ticket.pk)
    return render(request, "maintenance/ticket_form.html", {"form": form, "title": "Create Maintenance Request"})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(MaintenanceTicket.objects.select_related("tenant", "property", "room", "technician", "technician__user"), pk=pk)
    is_tech = ticket.technician and ticket.technician.user_id == request.user.id and request.user.role == "TECHNICIAN"
    allowed = request.user == ticket.tenant or request.user == ticket.property.owner or is_tech or request.user.role == "ADMIN"
    if not allowed:
        messages.error(request, "Access denied.")
        return redirect("accounts:dashboard")

    message_form = MaintenanceMessageForm(request.POST or None)
    if request.method == "POST":
        if request.user.role not in {"TENANT", "TECHNICIAN"} or not (request.user == ticket.tenant or is_tech):
            messages.error(request, "Only the tenant and assigned technician can send messages here.")
        elif message_form.is_valid():
            text = message_form.cleaned_data["message"].strip()
            MaintenanceMessage.objects.create(ticket=ticket, sender=request.user, message=text)
            if request.user == ticket.tenant and ticket.technician:
                _notify(ticket.technician.user, "New message from tenant", f"The tenant sent a clarification on ticket #{ticket.pk}: {text[:180]}", reverse("maintenance:ticket_detail", args=[ticket.pk]))
            elif is_tech:
                _notify(ticket.tenant, "Technician replied", f"Your technician replied to ticket #{ticket.pk}: {text[:180]}", reverse("maintenance:ticket_detail", args=[ticket.pk]))
            messages.success(request, "Message sent.")
            return redirect("maintenance:ticket_detail", ticket.pk)

    return render(request, "maintenance/ticket_detail.html", {
        "ticket": ticket,
        "conversation": ticket.messages.select_related("sender").all(),
        "message_form": message_form,
    })


@login_required
def owner_tickets(request):
    if request.user.role not in {"OWNER", "ADMIN"}:
        messages.error(request, "Access denied.")
        return redirect("accounts:dashboard")
    tickets = MaintenanceTicket.objects.all() if request.user.role == "ADMIN" else MaintenanceTicket.objects.filter(property__owner=request.user)
    tickets = tickets.select_related("tenant", "property", "room", "technician")
    return render(request, "maintenance/owner_tickets.html", {"tickets": tickets})


@login_required
def assign_ticket(request, pk):
    ticket = get_object_or_404(MaintenanceTicket, pk=pk, property__owner=request.user)
    if ticket.status not in {MaintenanceTicket.Status.OPEN, MaintenanceTicket.Status.ASSIGNED}:
        messages.warning(request, "This ticket cannot be reassigned at its current status.")
        return redirect("maintenance:owner_tickets")
    form = AssignTechnicianForm(request.POST or None, instance=ticket, owner=request.user)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.status = MaintenanceTicket.Status.ASSIGNED
        ticket.save()
        if ticket.technician:
            _notify(ticket.technician.user, "New maintenance request assigned", f"Ticket #{ticket.pk} for {ticket.property.title} has been assigned to you.", reverse("maintenance:technician_tickets"))
        _notify(ticket.tenant, "Technician assigned", f"A technician has been assigned to your maintenance ticket #{ticket.pk}.", reverse("maintenance:ticket_detail", args=[ticket.pk]))
        messages.success(request, "Technician assigned successfully.")
        return redirect("maintenance:owner_tickets")
    return render(request, "maintenance/assign_ticket.html", {"form": form, "ticket": ticket})


@login_required
def close_ticket(request, pk):
    ticket = get_object_or_404(MaintenanceTicket, pk=pk, property__owner=request.user)
    if request.method == "POST" and ticket.status == MaintenanceTicket.Status.RESOLVED:
        ticket.mark_closed()
        _notify(ticket.tenant, "Maintenance request closed", f"Your maintenance ticket #{ticket.pk} has been closed by the property owner.", reverse("maintenance:ticket_detail", args=[ticket.pk]))
        messages.success(request, "Maintenance ticket closed.")
    elif ticket.status != MaintenanceTicket.Status.RESOLVED:
        messages.warning(request, "Only resolved tickets can be closed.")
    return redirect("maintenance:owner_tickets")


@login_required
def technician_list(request):
    if request.user.role != "OWNER":
        messages.error(request, "Access denied.")
        return redirect("accounts:dashboard")
    technicians = Technician.objects.filter(owner=request.user).select_related("user")
    notifications = Notification.objects.filter(recipient=request.user, is_read=False)[:5]
    return render(request, "maintenance/technicians.html", {"technicians": technicians, "notifications": notifications})


@login_required
def technician_create(request):
    if request.user.role != "OWNER":
        messages.error(request, "Only property owners can create technician accounts.")
        return redirect("accounts:dashboard")
    form = TechnicianForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save(request.user)
        except IntegrityError:
            messages.error(request, "Could not create that technician. Please check the details and try again.")
        else:
            messages.success(request, "Technician account created. Give the username and password to the technician.")
            return redirect("maintenance:technicians")
    return render(request, "maintenance/technician_form.html", {"form": form, "title": "Create Technician Account"})


@login_required
def technician_delete(request, pk):
    if request.user.role != "OWNER":
        messages.error(request, "Only property owners can delete technician accounts.")
        return redirect("accounts:dashboard")
    technician = get_object_or_404(Technician.objects.select_related("user"), pk=pk, owner=request.user)
    if request.method == "POST":
        if technician.tickets.filter(status__in=[MaintenanceTicket.Status.ASSIGNED, MaintenanceTicket.Status.IN_PROGRESS]).exists():
            messages.error(request, "This technician has active work. Reassign those requests before deleting the account.")
            return redirect("maintenance:technicians")
        technician.user.delete()
        messages.success(request, "Technician account deleted successfully.")
        return redirect("maintenance:technicians")
    return render(request, "maintenance/technician_confirm_delete.html", {"technician": technician})


@login_required
def technician_account(request):
    if request.user.role != "TECHNICIAN":
        messages.error(request, "Only technicians can edit their account.")
        return redirect("accounts:dashboard")
    form = TechnicianAccountForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        old_username = request.user.username
        new_username = form.cleaned_data["username"]
        new_password = form.cleaned_data.get("new_password")
        changed = []
        if new_username != old_username:
            request.user.username = new_username
            changed.append("username")
        if new_password:
            request.user.set_password(new_password)
            changed.append("password")
        request.user.save()
        if new_password:
            update_session_auth_hash(request, request.user)
        technician = Technician.objects.select_related("owner").get(user=request.user)
        owner = technician.owner
        details = " and ".join(changed)
        _notify(owner, "Technician account updated", f"Technician {technician.name} has edited their {details}.", reverse("maintenance:technicians"))
        messages.success(request, "Your technician account was updated. The property owner has been notified.")
        return redirect("maintenance:technician_tickets")
    return render(request, "maintenance/technician_account.html", {"form": form})


@login_required
def technician_tickets(request):
    if request.user.role != "TECHNICIAN":
        messages.error(request, "Only technicians can access this dashboard.")
        return redirect("accounts:dashboard")
    tickets = MaintenanceTicket.objects.filter(technician__user=request.user).exclude(status=MaintenanceTicket.Status.CLOSED).select_related("property", "room", "tenant")
    stats = {
        "assigned": tickets.filter(status=MaintenanceTicket.Status.ASSIGNED).count(),
        "in_progress": tickets.filter(status=MaintenanceTicket.Status.IN_PROGRESS).count(),
        "resolved": tickets.filter(status=MaintenanceTicket.Status.RESOLVED).count(),
    }
    technician = Technician.objects.select_related("user", "owner").get(user=request.user)
    notifications = Notification.objects.filter(recipient=request.user, is_read=False)[:5]
    return render(request, "maintenance/technician_tickets.html", {"tickets": tickets, "stats": stats, "technician": technician, "notifications": notifications})


@login_required
def start_ticket(request, pk):
    ticket = get_object_or_404(MaintenanceTicket, pk=pk, technician__user=request.user)
    if request.method != "POST":
        return redirect("maintenance:technician_tickets")
    if ticket.status == MaintenanceTicket.Status.ASSIGNED:
        ticket.status = MaintenanceTicket.Status.IN_PROGRESS
        ticket.save(update_fields=["status", "updated_at"])
        _notify(ticket.tenant, "Technician started work", f"Your technician has started work on ticket #{ticket.pk}.", reverse("maintenance:ticket_detail", args=[ticket.pk]))
        messages.success(request, "Ticket marked as in progress.")
    return redirect("maintenance:technician_tickets")


@login_required
def resolve_ticket(request, pk):
    ticket = get_object_or_404(MaintenanceTicket, pk=pk, technician__user=request.user)
    if ticket.status != MaintenanceTicket.Status.IN_PROGRESS:
        messages.warning(request, "Only in-progress tickets can be resolved.")
        return redirect("maintenance:technician_tickets")
    if request.method == "POST":
        note = request.POST.get("technician_note", "").strip()
        if len(note) < 10:
            messages.error(request, "Please add a short explanation of what you fixed.")
        else:
            ticket.technician_note = note
            ticket.mark_resolved()
            ticket.save(update_fields=["technician_note", "updated_at"])
            _notify(ticket.tenant, "Maintenance request resolved", f"Your technician marked ticket #{ticket.pk} as resolved.", reverse("maintenance:ticket_detail", args=[ticket.pk]))
            messages.success(request, "Ticket marked as resolved.")
            return redirect("maintenance:technician_tickets")
    return render(request, "maintenance/resolve_ticket.html", {"ticket": ticket})


@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return redirect(request.POST.get("next") or "accounts:dashboard")
