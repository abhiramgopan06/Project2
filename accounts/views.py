import json
import secrets
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from bookings.reminders import rent_reminders_for
from maintenance.models import Notification

from .forms import ProfileForm, RegistrationForm
from .models import EmailVerification, User

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
OTP_RESEND_SECONDS = 30
MAX_OTP_ATTEMPTS = 5


def _new_otp():
    return f"{secrets.randbelow(900000) + 100000:06d}"


def _send_otp(user, request):
    now = timezone.now()
    code = _new_otp()
    verification, _ = EmailVerification.objects.get_or_create(user=user)
    verification.otp_hash = make_password(code)
    verification.expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
    verification.attempts = 0
    verification.verified = False
    verification.last_sent_at = now
    verification.save()
    send_mail(
        "Your Rental Platform verification code",
        f"Hello {user.first_name or user.username}, your Rental Platform verification code is {code}. It expires in {OTP_EXPIRY_MINUTES} minutes.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    request.session["otp_sent_at"] = now.isoformat()


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            existing = User.objects.filter(email__iexact=email).first()
            if existing and not existing.is_active:
                existing.delete()
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            try:
                _send_otp(user, request)
            except Exception:
                user.delete()
                messages.error(request, "We could not send the verification email. Check the email settings and try again.")
                return render(request, "accounts/register.html", {"form": form})
            request.session["pending_verification_user_id"] = user.pk
            messages.success(request, f"A verification code was sent to {user.email}.")
            return redirect("accounts:verify_email")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def verify_email(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    user_id = request.session.get("pending_verification_user_id")
    if not user_id:
        messages.info(request, "Please register first.")
        return redirect("accounts:register")

    try:
        user = User.objects.get(pk=user_id, is_active=False)
        verification = user.email_verification
    except (User.DoesNotExist, EmailVerification.DoesNotExist):
        request.session.pop("pending_verification_user_id", None)
        messages.error(request, "This verification session is no longer valid. Please register again.")
        return redirect("accounts:register")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "resend":
            now = timezone.now()
            if verification.last_sent_at and (now - verification.last_sent_at).total_seconds() < OTP_RESEND_SECONDS:
                messages.warning(request, "Please wait a few seconds before requesting another code.")
            else:
                try:
                    _send_otp(user, request)
                    messages.success(request, "A new verification code has been sent.")
                except Exception:
                    messages.error(request, "We could not send a new verification code. Please try again.")
            return redirect("accounts:verify_email")

        code = "".join(request.POST.get("otp", "").split())
        if not code.isdigit() or len(code) != OTP_LENGTH:
            messages.error(request, "Enter the 6-digit verification code.")
            return render(request, "accounts/verify_email.html", {"email": user.email})

        if verification.attempts >= MAX_OTP_ATTEMPTS:
            messages.error(request, "Too many incorrect attempts. Please send a new code.")
            return render(request, "accounts/verify_email.html", {"email": user.email, "locked": True})

        if timezone.now() > verification.expires_at:
            messages.error(request, "This code has expired. Please send a new code.")
            return render(request, "accounts/verify_email.html", {"email": user.email, "expired": True})

        verification.attempts += 1
        if check_password(code, verification.otp_hash):
            verification.verified = True
            verification.save(update_fields=["verified", "attempts"])
            user.is_active = True
            user.save(update_fields=["is_active"])
            request.session.pop("pending_verification_user_id", None)
            request.session.pop("otp_sent_at", None)
            messages.success(request, "Email verified successfully. You can now log in with your registered account.")
            return redirect("accounts:login")

        verification.save(update_fields=["attempts"])
        messages.error(request, "The verification code is incorrect. Please try again or resend a new code.")

    return render(request, "accounts/verify_email.html", {"email": user.email, "locked": verification.attempts >= MAX_OTP_ATTEMPTS})


def _google_configured():
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def google_login(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    if not _google_configured():
        messages.info(request, "Google sign-in needs Google OAuth credentials in the project settings.")
        return redirect("accounts:login")
    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = state
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return redirect(url)


def google_callback(request):
    if not _google_configured():
        return redirect("accounts:login")
    state = request.GET.get("state")
    expected_state = request.session.pop("google_oauth_state", None)
    if not state or state != expected_state:
        return HttpResponseBadRequest("Google sign-in could not be verified. Please try again.")
    if request.GET.get("error"):
        messages.info(request, "Google sign-in was cancelled.")
        return redirect("accounts:login")
    code = request.GET.get("code")
    if not code:
        messages.error(request, "Google sign-in did not return a valid code.")
        return redirect("accounts:login")

    token_data = urllib.parse.urlencode({
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    token_request = urllib.request.Request("https://oauth2.googleapis.com/token", data=token_data, method="POST")
    token_request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(token_request, timeout=10) as response:
            token_json = json.loads(response.read().decode())
        access_token = token_json.get("access_token")
        if not access_token:
            raise ValueError("No Google access token")
        user_request = urllib.request.Request("https://openidconnect.googleapis.com/v1/userinfo")
        user_request.add_header("Authorization", f"Bearer {access_token}")
        with urllib.request.urlopen(user_request, timeout=10) as response:
            google_user = json.loads(response.read().decode())
    except Exception:
        messages.error(request, "Google sign-in could not be completed. Please try again.")
        return redirect("accounts:login")

    email = google_user.get("email", "").strip().lower()
    if not email or not google_user.get("email_verified"):
        messages.error(request, "Google did not provide a verified email address.")
        return redirect("accounts:login")

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        base_username = "".join(ch for ch in email.split("@")[0].lower() if ch.isalnum() or ch in "._-")[:120] or "googleuser"
        username = base_username
        counter = 1
        while User.objects.filter(username__iexact=username).exists():
            counter += 1
            username = f"{base_username}{counter}"
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=google_user.get("given_name", ""),
            last_name=google_user.get("family_name", ""),
            role=User.Role.TENANT,
            is_active=True,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])

    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
    login(request, user)
    messages.success(request, f"Welcome, {user.first_name or user.username}!")
    return redirect("accounts:dashboard")


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
            next_url = request.GET.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect("accounts:dashboard")
        messages.error(request, "Invalid username or password. Verify your email first if you just registered.")

    return render(request, "accounts/login.html")


def technician_login(request):
    if request.user.is_authenticated:
        if request.user.role == "TECHNICIAN":
            return redirect("maintenance:technician_tickets")
        return redirect("accounts:dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.role == "TECHNICIAN":
            login(request, user)
            messages.success(request, f"Welcome, {user.first_name or user.username}!")
            return redirect("maintenance:technician_tickets")
        messages.error(request, "Invalid technician username or password.")
    return render(request, "accounts/technician_login.html")


@login_required
def user_logout(request):
    if request.method != "POST":
        return redirect("accounts:dashboard")
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
    return redirect("core:admin_dashboard")


@login_required
def owner_dashboard(request):
    if request.user.role != "OWNER":
        messages.error(request, "Access denied. Owner access is required.")
        return redirect("accounts:dashboard")
    notifications = Notification.objects.filter(recipient=request.user, is_read=False)[:5]
    return render(request, "accounts/owner_dashboard.html", {"notifications": notifications})


@login_required
def tenant_dashboard(request):
    if request.user.role != "TENANT":
        messages.error(request, "Access denied. Tenant access is required.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/tenant_dashboard.html", {"rent_reminders": rent_reminders_for(request.user)})


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
