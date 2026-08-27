from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import Amenity, Property


class PropertyAuthorizationTests(TestCase):
    def setUp(self):
        self.owner1 = User.objects.create_user(username="owner1", email="o1@example.com", password="StrongPass123!", role=User.Role.OWNER)
        self.owner2 = User.objects.create_user(username="owner2", email="o2@example.com", password="StrongPass123!", role=User.Role.OWNER)
        self.tenant = User.objects.create_user(username="tenant", email="t@example.com", password="StrongPass123!", role=User.Role.TENANT)
        self.property = Property.objects.create(
            owner=self.owner1, title="Test Home", description="A comfortable test property.",
            property_type=Property.PropertyType.HOUSE, location="Kochi", address="Test Road",
            number_of_rooms=2, rent=15000, available=True,
        )
        Amenity.objects.create(name="WiFi")

    def test_public_list_shows_available_property(self):
        response = self.client.get(reverse("properties:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Home")

    def test_owner_cannot_edit_another_owners_property(self):
        self.client.force_login(self.owner2)
        response = self.client.get(reverse("properties:update", args=[self.property.pk]))
        self.assertEqual(response.status_code, 404)

    def test_tenant_cannot_open_owner_property_list(self):
        self.client.force_login(self.tenant)
        response = self.client.get(reverse("properties:owner_property_list"))
        self.assertRedirects(response, reverse("accounts:dashboard"))
