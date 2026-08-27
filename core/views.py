from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.models import User
from bookings.models import Booking, RentalRequest
from maintenance.models import MaintenanceTicket
from payments.models import Payment
from properties.models import Property
from .forms import PropertyReportForm
from .models import PropertyReport


def home(request):
    featured = Property.objects.filter(available=True).prefetch_related("images")[:6]
    return render(request, "home.html", {"featured_properties": featured})


def _admin_only(request):
    return request.user.is_authenticated and (request.user.is_superuser or request.user.role == User.Role.ADMIN)


@login_required
def report_property(request, pk):
    if request.user.role not in {User.Role.TENANT, User.Role.OWNER}:
        messages.error(request, "Only registered users can report a property.")
        return redirect("properties:detail", pk=pk)
    property_obj = get_object_or_404(Property, pk=pk)
    existing = PropertyReport.objects.filter(property=property_obj, reporter=request.user, status__in=[PropertyReport.Status.OPEN, PropertyReport.Status.REVIEWING]).exists()
    if existing:
        messages.info(request, "You already have an active report for this property.")
        return redirect("properties:detail", pk=pk)
    if request.method == "POST":
        form = PropertyReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.property = property_obj
            report.reporter = request.user
            report.save()
            if property_obj.owner.email:
                send_mail(
                    f"Property report received - {property_obj.title}",
                    f"A user reported your property '{property_obj.title}'. Reason: {report.get_reason_display()}. Please review the listing.",
                    None, [property_obj.owner.email], fail_silently=True,
                )
            messages.success(request, "Your report has been submitted to the platform team.")
            return redirect("properties:detail", pk=pk)
    else:
        form = PropertyReportForm()
    return render(request, "core/report_property.html", {"form": form, "property": property_obj})


@login_required
def my_reports(request):
    reports = PropertyReport.objects.filter(reporter=request.user).select_related("property")
    return render(request, "core/my_reports.html", {"reports": reports})


@login_required
def admin_dashboard(request):
    if not _admin_only(request):
        messages.error(request, "Admin access is required.")
        return redirect("accounts:dashboard")
    context = {
        "total_users": User.objects.count(),
        "owners": User.objects.filter(role=User.Role.OWNER).count(),
        "tenants": User.objects.filter(role=User.Role.TENANT).count(),
        "technicians": User.objects.filter(role=User.Role.TECHNICIAN).count(),
        "properties": Property.objects.count(),
        "available_properties": Property.objects.filter(available=True).count(),
        "pending_requests": RentalRequest.objects.filter(status=RentalRequest.Status.PENDING).count(),
        "confirmed_bookings": Booking.objects.filter(status=Booking.Status.CONFIRMED).count(),
        "successful_payments": Payment.objects.filter(status=Payment.Status.SUCCESS).count(),
        "payment_total": Payment.objects.filter(status=Payment.Status.SUCCESS).aggregate(total=Sum('amount'))['total'] or 0,
        "open_tickets": MaintenanceTicket.objects.filter(status__in=[MaintenanceTicket.Status.OPEN, MaintenanceTicket.Status.ASSIGNED, MaintenanceTicket.Status.IN_PROGRESS]).count(),
        "open_reports": PropertyReport.objects.filter(status__in=[PropertyReport.Status.OPEN, PropertyReport.Status.REVIEWING]).count(),
        "recent_reports": PropertyReport.objects.select_related("property", "reporter")[:8],
        "recent_bookings": Booking.objects.select_related("tenant", "property")[:8],
        "stats": [("Users", User.objects.count()), ("Owners", User.objects.filter(role=User.Role.OWNER).count()), ("Tenants", User.objects.filter(role=User.Role.TENANT).count()), ("Properties", Property.objects.count()), ("Available", Property.objects.filter(available=True).count()), ("Pending Requests", RentalRequest.objects.filter(status=RentalRequest.Status.PENDING).count()), ("Confirmed Bookings", Booking.objects.filter(status=Booking.Status.CONFIRMED).count()), ("Open Tickets", MaintenanceTicket.objects.filter(status__in=[MaintenanceTicket.Status.OPEN, MaintenanceTicket.Status.ASSIGNED, MaintenanceTicket.Status.IN_PROGRESS]).count())],
    }
    return render(request, "core/admin_dashboard.html", context)


@login_required
def admin_reports(request):
    if not _admin_only(request):
        messages.error(request, "Admin access is required.")
        return redirect("accounts:dashboard")
    reports = PropertyReport.objects.select_related("property", "reporter")
    status = request.GET.get("status", "").strip()
    if status in dict(PropertyReport.Status.choices):
        reports = reports.filter(status=status)
    return render(request, "core/admin_reports.html", {"reports": reports, "statuses": PropertyReport.Status.choices, "selected_status": status})


@login_required
def admin_report_update(request, pk):
    if not _admin_only(request):
        messages.error(request, "Admin access is required.")
        return redirect("accounts:dashboard")
    report = get_object_or_404(PropertyReport.objects.select_related("property", "reporter"), pk=pk)
    if request.method == "POST":
        status = request.POST.get("status")
        note = request.POST.get("admin_note", "").strip()
        if status not in dict(PropertyReport.Status.choices):
            messages.error(request, "Invalid report status.")
        else:
            report.status = status
            report.admin_note = note
            report.save(update_fields=["status", "admin_note", "updated_at"])
            if report.reporter.email:
                send_mail(
                    f"Property report update - {report.property.title}",
                    f"Your report #{report.pk} is now {report.get_status_display()}.\n\nAdmin note: {note or 'No additional note.'}",
                    None, [report.reporter.email], fail_silently=True,
                )
            messages.success(request, "Report updated and the reporter was notified.")
            return redirect("core:admin_reports")
    return render(request, "core/admin_report_update.html", {"report": report, "statuses": PropertyReport.Status.choices})
