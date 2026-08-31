from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .forms import PropertyForm
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
        # /accounts/dashboard/ redirects on again to the role-specific
        # dashboard, so the intermediate hop returns 302, not 200.
        self.assertRedirects(response, reverse("accounts:dashboard"), target_status_code=302)


class PropertyMapLocationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", email="o@example.com", password="StrongPass123!", role=User.Role.OWNER)
        self.model_data = {
            "title": "Map Home", "description": "Has coordinates.", "property_type": Property.PropertyType.HOUSE,
            "location": "Kochi", "address": "Test Road", "number_of_rooms": 2, "rent": 15000,
        }
        self.form_data = {**self.model_data, "amenities": []}

    def test_property_without_coordinates_has_no_map(self):
        property_ = Property.objects.create(owner=self.owner, **self.model_data)
        self.assertFalse(property_.has_map_location)
        self.assertEqual(property_.map_embed_url, "")

    def test_property_with_coordinates_builds_map_embed_url(self):
        property_ = Property.objects.create(owner=self.owner, latitude=9.9312, longitude=76.2673, **self.model_data)
        self.assertTrue(property_.has_map_location)
        self.assertIn("9.9312", property_.map_embed_url)
        self.assertIn("76.2673", property_.map_embed_url)

    def test_form_rejects_only_one_coordinate(self):
        form = PropertyForm(data={**self.form_data, "latitude": 9.9312})
        self.assertFalse(form.is_valid())
        self.assertIn("longitude", form.errors)

    def test_form_accepts_both_coordinates_or_neither(self):
        form = PropertyForm(data={**self.form_data, "latitude": 9.9312, "longitude": 76.2673})
        self.assertTrue(form.is_valid())
        form = PropertyForm(data=self.form_data)
        self.assertTrue(form.is_valid())
