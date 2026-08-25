from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PropertyForm, PropertyImageForm, RoomForm
from .models import Property, PropertyImage, Room


def property_list(request):
    """Public/tenant property discovery page. Only currently available listings are shown."""
    properties = (
        Property.objects.filter(available=True)
        .select_related("owner")
        .prefetch_related("images", "amenities", "rooms")
    )

    query = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    property_type = request.GET.get("property_type", "").strip()
    min_rent = request.GET.get("min_rent", "").strip()
    max_rent = request.GET.get("max_rent", "").strip()

    if query:
        properties = properties.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(location__icontains=query)
            | Q(address__icontains=query)
        )
    if location:
        properties = properties.filter(location__icontains=location)
    if property_type in dict(Property.PropertyType.choices):
        properties = properties.filter(property_type=property_type)

    rent_error = ""
    if min_rent:
        try:
            properties = properties.filter(rent__gte=float(min_rent))
        except (TypeError, ValueError):
            rent_error = "Minimum rent must be a valid number."
    if max_rent:
        try:
            properties = properties.filter(rent__lte=float(max_rent))
        except (TypeError, ValueError):
            rent_error = "Maximum rent must be a valid number."

    paginator = Paginator(properties, 9)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(
        request,
        "properties/property_list.html",
        {
            "properties": page_obj,
            "page_obj": page_obj,
            "property_types": Property.PropertyType.choices,
            "filters": request.GET,
            "rent_error": rent_error,
            "result_count": paginator.count,
        },
    )


def property_detail(request, pk):
    property_obj = get_object_or_404(
        Property.objects.select_related("owner").prefetch_related("images", "rooms", "amenities"),
        pk=pk,
    )
    return render(request, "properties/property_detail.html", {"property": property_obj})


def owner_required(view_func):
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if request.user.role != "OWNER":
            messages.error(request, "Owner access is required.")
            return redirect("accounts:dashboard")
        return view_func(request, *args, **kwargs)
    wrapped.__name__ = view_func.__name__
    wrapped.__doc__ = view_func.__doc__
    return wrapped


@owner_required

def owner_property_list(request):
    properties = Property.objects.filter(owner=request.user).prefetch_related("images", "rooms")
    return render(request, "properties/owner_property_list.html", {"properties": properties})


@owner_required

def property_create(request):
    if request.method == "POST":
        form = PropertyForm(request.POST)
        if form.is_valid():
            property_obj = form.save(commit=False)
            property_obj.owner = request.user
            property_obj.save()
            form.save_m2m()
            messages.success(request, "Property created successfully.")
            return redirect("properties:owner_property_detail", pk=property_obj.pk)
    else:
        form = PropertyForm()
    return render(request, "properties/property_form.html", {"form": form, "page_title": "Add Property"})


@owner_required

def property_update(request, pk):
    property_obj = get_object_or_404(Property, pk=pk, owner=request.user)
    if request.method == "POST":
        form = PropertyForm(request.POST, instance=property_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Property updated successfully.")
            return redirect("properties:owner_property_detail", pk=property_obj.pk)
    else:
        form = PropertyForm(instance=property_obj)
    return render(request, "properties/property_form.html", {"form": form, "page_title": "Edit Property", "property": property_obj})


@owner_required

def property_delete(request, pk):
    property_obj = get_object_or_404(Property, pk=pk, owner=request.user)
    if request.method == "POST":
        property_obj.delete()
        messages.success(request, "Property deleted successfully.")
        return redirect("properties:owner_property_list")
    return render(request, "properties/property_confirm_delete.html", {"property": property_obj})


@owner_required

def owner_property_detail(request, pk):
    property_obj = get_object_or_404(
        Property.objects.prefetch_related("images", "rooms", "amenities"),
        pk=pk,
        owner=request.user,
    )
    image_form = PropertyImageForm()
    return render(request, "properties/owner_property_detail.html", {"property": property_obj, "image_form": image_form})


@owner_required

def property_image_add(request, pk):
    property_obj = get_object_or_404(Property, pk=pk, owner=request.user)
    if request.method != "POST":
        return redirect("properties:owner_property_detail", pk=pk)
    form = PropertyImageForm(request.POST, request.FILES)
    if form.is_valid():
        image = form.save(commit=False)
        image.property = property_obj
        image.save()
        messages.success(request, "Property image uploaded successfully.")
    else:
        messages.error(request, "Please select a valid image.")
    return redirect("properties:owner_property_detail", pk=pk)


@owner_required

def property_image_delete(request, pk, image_pk):
    property_obj = get_object_or_404(Property, pk=pk, owner=request.user)
    image = get_object_or_404(PropertyImage, pk=image_pk, property=property_obj)
    if request.method == "POST":
        was_primary = image.is_primary
        image.delete()
        if was_primary:
            replacement = property_obj.images.first()
            if replacement:
                replacement.is_primary = True
                replacement.save()
        messages.success(request, "Property image deleted successfully.")
    return redirect("properties:owner_property_detail", pk=pk)


@owner_required

def room_create(request, pk):
    property_obj = get_object_or_404(Property, pk=pk, owner=request.user)
    if request.method == "POST":
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.property = property_obj
            room.save()
            messages.success(request, "Room added successfully.")
            return redirect("properties:owner_property_detail", pk=pk)
    else:
        form = RoomForm()
    return render(request, "properties/room_form.html", {"form": form, "property": property_obj, "page_title": "Add Room"})


@owner_required

def room_update(request, pk, room_pk):
    property_obj = get_object_or_404(Property, pk=pk, owner=request.user)
    room = get_object_or_404(Room, pk=room_pk, property=property_obj)
    if request.method == "POST":
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, "Room updated successfully.")
            return redirect("properties:owner_property_detail", pk=pk)
    else:
        form = RoomForm(instance=room)
    return render(request, "properties/room_form.html", {"form": form, "property": property_obj, "room": room, "page_title": "Edit Room"})


@owner_required

def room_delete(request, pk, room_pk):
    property_obj = get_object_or_404(Property, pk=pk, owner=request.user)
    room = get_object_or_404(Room, pk=room_pk, property=property_obj)
    if request.method == "POST":
        room.delete()
        messages.success(request, "Room deleted successfully.")
        return redirect("properties:owner_property_detail", pk=pk)
    return render(request, "properties/room_confirm_delete.html", {"property": property_obj, "room": room})
