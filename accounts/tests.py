from unittest.mock import patch

from django.contrib.auth.hashers import check_password
from django.test import TestCase
from django.urls import reverse

from .models import EmailVerification, User


class AuthenticationTests(TestCase):
    def setUp(self):
        self.tenant = User.objects.create_user(
            username="tenant1", email="tenant@example.com", password="StrongPass123!", role=User.Role.TENANT
        )
        self.owner = User.objects.create_user(
            username="owner1", email="owner@example.com", password="StrongPass123!", role=User.Role.OWNER
        )

    @patch("accounts.views.send_mail")
    @patch("accounts.views._new_otp", return_value="123456")
    def test_registration_requires_email_verification(self, mock_otp, mock_send_mail):
        response = self.client.post(reverse("accounts:register"), {
            "username": "newtenant", "first_name": "New", "last_name": "Tenant",
            "email": "newtenant@example.com", "phone": "9876543210", "role": "TENANT",
            "password1": "StrongPass123!", "password2": "StrongPass123!",
        })
        self.assertRedirects(response, reverse("accounts:verify_email"))
        user = User.objects.get(username="newtenant")
        self.assertFalse(user.is_active)
        self.assertTrue(check_password("123456", user.email_verification.otp_hash))
        mock_send_mail.assert_called_once()

    @patch("accounts.views.send_mail")
    @patch("accounts.views._new_otp", return_value="123456")
    def test_correct_otp_activates_account_and_returns_to_login(self, mock_otp, mock_send_mail):
        self.client.post(reverse("accounts:register"), {
            "username": "verifieduser", "first_name": "Verified", "last_name": "User",
            "email": "verified@example.com", "phone": "9876543210", "role": "TENANT",
            "password1": "StrongPass123!", "password2": "StrongPass123!",
        })
        response = self.client.post(reverse("accounts:verify_email"), {"otp": "123456"})
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertTrue(User.objects.get(username="verifieduser").is_active)
        self.assertTrue(User.objects.get(username="verifieduser").email_verification.verified)

    @patch("accounts.views.send_mail")
    @patch("accounts.views._new_otp", return_value="123456")
    def test_wrong_otp_does_not_activate_account(self, mock_otp, mock_send_mail):
        self.client.post(reverse("accounts:register"), {
            "username": "wrongotp", "first_name": "Wrong", "last_name": "Otp",
            "email": "wrongotp@example.com", "phone": "9876543210", "role": "TENANT",
            "password1": "StrongPass123!", "password2": "StrongPass123!",
        })
        response = self.client.post(reverse("accounts:verify_email"), {"otp": "000000"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.get(username="wrongotp").is_active)
        self.assertEqual(EmailVerification.objects.get(user__username="wrongotp").attempts, 1)

    def test_owner_cannot_open_tenant_dashboard(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("accounts:tenant_dashboard"))
        self.assertRedirects(response, reverse("accounts:dashboard"), target_status_code=302)

    def test_logout_requires_post(self):
        self.client.force_login(self.tenant)
        response = self.client.get(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:dashboard"), target_status_code=302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_goes_back_to_the_page_the_user_came_from(self):
        response = self.client.post(
            reverse("accounts:login") + "?next=/properties/",
            {"username": "tenant1", "password": "StrongPass123!"},
        )
        self.assertRedirects(response, "/properties/")

    def test_login_ignores_next_pointing_to_another_website(self):
        response = self.client.post(
            reverse("accounts:login") + "?next=https://evil.example.com/",
            {"username": "tenant1", "password": "StrongPass123!"},
        )
        self.assertRedirects(response, reverse("accounts:dashboard"), target_status_code=302)
