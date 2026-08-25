from django.contrib import admin
from .models import Booking, RentalRequest


@admin.register(RentalRequest)
class RentalRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "property", "room", "move_in_date", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("tenant__username", "tenant__email", "property__title")
    list_select_related = ("tenant", "property", "room")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "property", "room", "start_date", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("tenant__username", "tenant__email", "property__title")
    list_select_related = ("tenant", "property", "room")
