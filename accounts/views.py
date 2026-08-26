from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import redirect, render

from .forms import ProfileForm, RegistrationForm


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_mail(
                "Welcome to Rental Platform",
                f"Hello {user.first_name or user.username}, your Rental Platform account has been created successfully.",
                None,
                [user.email],
                fail_silently=True,
            )
            messages.success(request, "Your account has been created successfully. Welcome!")
            login(request, user)
            return redirect("accounts:dashboard")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect("accounts:dashboard")

        messages.error(request, "Invalid username or password.")

    return render(request, "accounts/login.html")


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("core:home")


@login_required
def dashboard(request):
    if request.user.is_superuser or request.user.role == "ADMIN":
        return redirect("accounts:admin_dashboard")
    if request.user.role == "OWNER":
        return redirect("accounts:owner_dashboard")
    if request.user.role == "TECHNICIAN":
        return redirect("maintenance:technician_tickets")
    return redirect("accounts:tenant_dashboard")


@login_required
def admin_dashboard(request):
    if not (request.user.is_superuser or request.user.role == "ADMIN"):
        messages.error(request, "Access denied.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/admin_dashboard.html")


@login_required
def owner_dashboard(request):
    if request.user.role != "OWNER":
        messages.error(request, "Access denied. Owner access is required.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/owner_dashboard.html")


@login_required
def tenant_dashboard(request):
    if request.user.role != "TENANT":
        messages.error(request, "Access denied. Tenant access is required.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/tenant_dashboard.html")


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)

    return render(request, "accounts/profile.html", {"form": form})
