from django.test import TestCase
from django.urls import reverse

from .models import User


class AuthenticationTests(TestCase):
    def setUp(self):
        self.tenant = User.objects.create_user(
            username="tenant1", email="tenant@example.com", password="StrongPass123!", role=User.Role.TENANT
        )
        self.owner = User.objects.create_user(
            username="owner1", email="owner@example.com", password="StrongPass123!", role=User.Role.OWNER
        )

    def test_tenant_registration_redirects_to_dashboard(self):
        response = self.client.post(reverse("accounts:register"), {
            "username": "newtenant", "first_name": "New", "last_name": "Tenant",
            "email": "newtenant@example.com", "phone": "9876543210", "role": "TENANT",
            "password1": "StrongPass123!", "password2": "StrongPass123!",
        })
        # /accounts/dashboard/ itself redirects on to the role-specific
        # dashboard, so the intermediate hop returns 302, not 200.
        self.assertRedirects(response, reverse("accounts:dashboard"), target_status_code=302)
        self.assertTrue(User.objects.filter(username="newtenant").exists())

    def test_owner_cannot_open_tenant_dashboard(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("accounts:tenant_dashboard"))
        self.assertRedirects(response, reverse("accounts:dashboard"), target_status_code=302)

    def test_logout_requires_post(self):
        self.client.force_login(self.tenant)
        response = self.client.get(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:dashboard"), target_status_code=302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
