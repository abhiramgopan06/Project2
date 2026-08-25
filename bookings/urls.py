from django.urls import path
from . import views

app_name = "bookings"

urlpatterns = [
    path("request/<int:property_pk>/", views.create_request, name="create_request"),
    path("my-requests/", views.my_requests, name="my_requests"),
    path("my-bookings/", views.my_bookings, name="my_bookings"),
    path("owner/requests/", views.owner_requests, name="owner_requests"),
    path("owner/requests/<int:pk>/approve/", views.approve_request, name="approve_request"),
    path("owner/requests/<int:pk>/reject/", views.reject_request, name="reject_request"),
]
