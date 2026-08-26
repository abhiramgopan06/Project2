from django.urls import path

from . import views

app_name = "maintenance"

urlpatterns = [
    path("", views.tenant_tickets, name="tenant_tickets"),
    path("create/", views.create_ticket, name="create_ticket"),
    path("ticket/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("owner/", views.owner_tickets, name="owner_tickets"),
    path("owner/ticket/<int:pk>/assign/", views.assign_ticket, name="assign_ticket"),
    path("owner/ticket/<int:pk>/close/", views.close_ticket, name="close_ticket"),
    path("technicians/", views.technician_list, name="technicians"),
    path("technicians/add/", views.technician_create, name="technician_create"),
    path("technician/tickets/", views.technician_tickets, name="technician_tickets"),
    path("technician/ticket/<int:pk>/start/", views.start_ticket, name="start_ticket"),
    path("technician/ticket/<int:pk>/resolve/", views.resolve_ticket, name="resolve_ticket"),
]
