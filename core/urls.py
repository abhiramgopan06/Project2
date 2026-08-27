from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("property/<int:pk>/report/", views.report_property, name="report_property"),
    path("my-reports/", views.my_reports, name="my_reports"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/reports/", views.admin_reports, name="admin_reports"),
    path("admin-dashboard/reports/<int:pk>/update/", views.admin_report_update, name="admin_report_update"),
]
