from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from properties.models import Property


class ReportTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="StrongPass123!", role=User.Role.OWNER)
        self.tenant = User.objects.create_user(username="tenant", email="tenant@example.com", password="StrongPass123!", role=User.Role.TENANT)
        self.property = Property.objects.create(
            owner=self.owner, title="Reported Home", description="A property that can be reported.",
            property_type=Property.PropertyType.APARTMENT, location="Kochi", address="Main Road",
            number_of_rooms=1, rent=10000, available=True,
        )

    def test_tenant_can_open_report_form(self):
        self.client.force_login(self.tenant)
        response = self.client.get(reverse("core:report_property", args=[self.property.pk]))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_cannot_report(self):
        response = self.client.get(reverse("core:report_property", args=[self.property.pk]))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('core:report_property', args=[self.property.pk])}")
