from django.contrib import admin
from .models import Booking, RentalRequest


@admin.register(RentalRequest)
class RentalRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "property", "room", "move_in_date", "duration_months", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("tenant__username", "tenant__email", "property__title")
    list_select_related = ("tenant", "property", "room")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "property", "room", "start_date", "duration_months", "end_date", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("tenant__username", "tenant__email", "property__title")
    list_select_related = ("tenant", "property", "room")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
