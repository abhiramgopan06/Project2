from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from bookings.models import Booking

from .forms import AssignTechnicianForm, MaintenanceTicketForm, TechnicianForm
from .models import MaintenanceTicket, Technician


def _email(subject, message, recipient):
    if recipient:
        send_mail(subject, message, None, [recipient], fail_silently=True)


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
    if request.method == "POST":
        form = MaintenanceTicketForm(request.POST, tenant=request.user)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.tenant = request.user
            booking = confirmed.filter(property=ticket.property, room=ticket.room).first() or confirmed.filter(property=ticket.property).first()
            if not booking:
                form.add_error("property", "You do not have a confirmed booking for this property/room.")
            else:
                ticket.booking = booking
                ticket.save()
                owner = ticket.property.owner
                _email("New maintenance request", f"A new maintenance request was raised for {ticket.property.title}: {ticket.title}", owner.email)
                _email("Maintenance request created", f"Your maintenance ticket #{ticket.pk} has been created.", request.user.email)
                messages.success(request, "Maintenance request created successfully.")
                return redirect("maintenance:ticket_detail", ticket.pk)
    else:
        form = MaintenanceTicketForm(tenant=request.user)
    return render(request, "maintenance/ticket_form.html", {"form": form, "title": "Create Maintenance Request"})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(MaintenanceTicket.objects.select_related("tenant", "property", "room", "technician"), pk=pk)
    allowed = request.user == ticket.tenant or request.user == ticket.property.owner or (ticket.technician and ticket.technician.user_id == request.user.id and request.user.role == "TECHNICIAN") or request.user.role == "ADMIN"
    if not allowed:
        messages.error(request, "Access denied.")
        return redirect("accounts:dashboard")
    return render(request, "maintenance/ticket_detail.html", {"ticket": ticket})


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
    if request.method == "POST":
        form = AssignTechnicianForm(request.POST, instance=ticket, owner=request.user)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.status = MaintenanceTicket.Status.ASSIGNED
            ticket.save()
            if ticket.technician:
                _email("Maintenance ticket assigned", f"Ticket #{ticket.pk} has been assigned to you: {ticket.title}", ticket.technician.email)
            _email("Maintenance request assigned", f"Your maintenance ticket #{ticket.pk} has been assigned to a technician.", ticket.tenant.email)
            messages.success(request, "Technician assigned successfully.")
            return redirect("maintenance:owner_tickets")
    else:
        form = AssignTechnicianForm(instance=ticket, owner=request.user)
    return render(request, "maintenance/assign_ticket.html", {"form": form, "ticket": ticket})


@login_required
def close_ticket(request, pk):
    ticket = get_object_or_404(MaintenanceTicket, pk=pk, property__owner=request.user)
    if ticket.status != MaintenanceTicket.Status.RESOLVED:
        messages.warning(request, "Only resolved tickets can be closed.")
    else:
        ticket.mark_closed()
        _email("Maintenance request closed", f"Your maintenance ticket #{ticket.pk} has been closed.", ticket.tenant.email)
        messages.success(request, "Maintenance ticket closed.")
    return redirect("maintenance:owner_tickets")


@login_required
def technician_list(request):
    if request.user.role != "OWNER":
        messages.error(request, "Access denied.")
        return redirect("accounts:dashboard")
    technicians = Technician.objects.filter(owner=request.user)
    return render(request, "maintenance/technicians.html", {"technicians": technicians})


@login_required
def technician_create(request):
    if request.user.role != "OWNER":
        messages.error(request, "Access denied.")
        return redirect("accounts:dashboard")
    form = TechnicianForm(request.POST or None)
    if form.is_valid():
        form.save(request.user)
        messages.success(request, "Technician added successfully.")
        return redirect("maintenance:technicians")
    return render(request, "maintenance/technician_form.html", {"form": form, "title": "Add Technician"})


@login_required
def technician_tickets(request):
    if request.user.role != "TECHNICIAN":
        messages.error(request, "Only technicians can access this dashboard.")
        return redirect("accounts:dashboard")
    tickets = MaintenanceTicket.objects.filter(technician__user=request.user).exclude(status=MaintenanceTicket.Status.CLOSED).select_related("property", "room", "tenant")
    return render(request, "maintenance/technician_tickets.html", {"tickets": tickets})


@login_required
def start_ticket(request, pk):
    ticket = get_object_or_404(MaintenanceTicket, pk=pk, technician__user=request.user)
    if ticket.status == MaintenanceTicket.Status.ASSIGNED:
        ticket.status = MaintenanceTicket.Status.IN_PROGRESS
        ticket.save(update_fields=["status", "updated_at"])
        _email("Maintenance request in progress", f"Your maintenance ticket #{ticket.pk} is now in progress.", ticket.tenant.email)
        messages.success(request, "Ticket marked as in progress.")
    return redirect("maintenance:technician_tickets")


@login_required
def resolve_ticket(request, pk):
    ticket = get_object_or_404(MaintenanceTicket, pk=pk, technician__user=request.user)
    if ticket.status != MaintenanceTicket.Status.IN_PROGRESS:
        messages.warning(request, "Only in-progress tickets can be resolved.")
        return redirect("maintenance:technician_tickets")
    if request.method == "POST":
        ticket.technician_note = request.POST.get("technician_note", "").strip()
        ticket.mark_resolved()
        ticket.technician_note = request.POST.get("technician_note", "").strip()
        ticket.save(update_fields=["technician_note", "updated_at"])
        _email("Maintenance request resolved", f"Your maintenance ticket #{ticket.pk} has been marked resolved.", ticket.tenant.email)
        messages.success(request, "Ticket marked as resolved.")
        return redirect("maintenance:technician_tickets")
    return render(request, "maintenance/resolve_ticket.html", {"ticket": ticket})
