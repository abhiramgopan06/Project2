from django.contrib import admin

from .models import Amenity, Property, PropertyImage, Room


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 0


class RoomInline(admin.TabularInline):
    model = Room
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "property_type", "location", "rent", "available", "created_at")
    list_filter = ("property_type", "available", "amenities")
    search_fields = ("title", "location", "address", "owner__username", "owner__email")
    filter_horizontal = ("amenities",)
    inlines = [PropertyImageInline, RoomInline]


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ("property", "is_primary", "uploaded_at")
    list_filter = ("is_primary",)
    search_fields = ("property__title", "property__owner__username")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("property", "room_number", "room_type", "rent", "available")
    list_filter = ("room_type", "available")
    search_fields = ("property__title", "room_number")


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    search_fields = ("name",)
