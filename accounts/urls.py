from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("owner-dashboard/", views.owner_dashboard, name="owner_dashboard"),
    path("tenant-dashboard/", views.tenant_dashboard, name="tenant_dashboard"),
    path("profile/", views.profile, name="profile"),
]
