from datetime import date, timedelta

from django.core import mail
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from properties.models import Property, Room

from .forms import RentalRequestForm
from .models import Booking, RentalRequest
from .utils import add_months, format_duration, lease_end_date


class DurationHelperTests(SimpleTestCase):
    def test_add_months_clamps_to_month_end(self):
        self.assertEqual(add_months(date(2027, 1, 31), 1), date(2027, 2, 28))
        self.assertEqual(add_months(date(2028, 1, 31), 1), date(2028, 2, 29))

    def test_add_months_rolls_over_year(self):
        self.assertEqual(add_months(date(2027, 11, 15), 3), date(2028, 2, 15))

    def test_lease_end_date_is_inclusive(self):
        self.assertEqual(lease_end_date(date(2027, 1, 1), 1), date(2027, 1, 31))
        self.assertEqual(lease_end_date(date(2027, 1, 1), 12), date(2027, 12, 31))

    def test_lease_end_date_handles_missing_values(self):
        self.assertIsNone(lease_end_date(None, 3))
        self.assertIsNone(lease_end_date(date(2027, 1, 1), None))

    def test_format_duration(self):
        self.assertEqual(format_duration(1), "1 month")
        self.assertEqual(format_duration(6), "6 months")
        self.assertEqual(format_duration(12), "1 year")
        self.assertEqual(format_duration(18), "1 year 6 months")
        self.assertEqual(format_duration(24), "2 years")


class RentalDurationTestBase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="StrongPass123!", role=User.Role.OWNER
        )
        self.tenant = User.objects.create_user(
            username="tenant", email="tenant@example.com", password="StrongPass123!", role=User.Role.TENANT
        )
        self.property = Property.objects.create(
            owner=self.owner, title="Duration Home", description="A home used for duration tests.",
            property_type=Property.PropertyType.HOUSE, location="Kochi", address="Test Road",
            number_of_rooms=2, rent=15000, available=True,
        )
        self.move_in = timezone.localdate() + timedelta(days=10)

    def form_data(self, **overrides):
        data = {
            "room": "",
            "move_in_date": self.move_in.isoformat(),
            "duration_months": 6,
            "message": "Looking forward to it.",
        }
        data.update(overrides)
        return data

    def make_request(self, **overrides):
        values = {
            "tenant": self.tenant, "property": self.property,
            "move_in_date": self.move_in, "duration_months": 6,
        }
        values.update(overrides)
        return RentalRequest.objects.create(**values)


class RentalRequestFormDurationTests(RentalDurationTestBase):
    def test_valid_duration_is_accepted(self):
        form = RentalRequestForm(data=self.form_data(), property_obj=self.property)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["duration_months"], 6)

    def test_boundary_durations_are_accepted(self):
        for months in (1, 60):
            form = RentalRequestForm(data=self.form_data(duration_months=months), property_obj=self.property)
            self.assertTrue(form.is_valid(), (months, form.errors))

    def test_duration_below_minimum_is_rejected(self):
        form = RentalRequestForm(data=self.form_data(duration_months=0), property_obj=self.property)
        self.assertFalse(form.is_valid())
        self.assertIn("duration_months", form.errors)

    def test_duration_above_maximum_is_rejected(self):
        form = RentalRequestForm(data=self.form_data(duration_months=61), property_obj=self.property)
        self.assertFalse(form.is_valid())
        self.assertIn("duration_months", form.errors)

    def test_duration_is_required_and_must_be_a_number(self):
        for bad in ("", "abc", "2.5"):
            form = RentalRequestForm(data=self.form_data(duration_months=bad), property_obj=self.property)
            self.assertFalse(form.is_valid(), bad)
            self.assertIn("duration_months", form.errors)


class RentalRequestRoomTests(RentalDurationTestBase):
    """Choosing a specific room used to be rejected even when it belonged to the property."""

    def setUp(self):
        super().setUp()
        self.room = Room.objects.create(property=self.property, room_number="101", rent=5000)

    def test_room_of_this_property_is_accepted(self):
        form = RentalRequestForm(data=self.form_data(room=self.room.pk), property_obj=self.property)
        self.assertTrue(form.is_valid(), form.errors)

    def test_room_of_another_property_is_rejected(self):
        other = Property.objects.create(
            owner=self.owner, title="Other Home", description="Another home for the test.",
            property_type=Property.PropertyType.HOUSE, location="Kochi", address="Other Road",
            number_of_rooms=1, rent=9000, available=True,
        )
        other_room = Room.objects.create(property=other, room_number="7", rent=3000)
        form = RentalRequestForm(data=self.form_data(room=other_room.pk), property_obj=self.property)
        self.assertFalse(form.is_valid())
        self.assertIn("room", form.errors)

    def test_tenant_can_request_a_specific_room(self):
        self.client.force_login(self.tenant)
        response = self.client.post(
            reverse("bookings:create_request", args=[self.property.pk]), self.form_data(room=self.room.pk)
        )
        self.assertRedirects(response, reverse("bookings:my_requests"))
        self.assertEqual(RentalRequest.objects.get().room, self.room)


class RentalRequestDurationFlowTests(RentalDurationTestBase):
    def test_tenant_request_stores_duration(self):
        self.client.force_login(self.tenant)
        response = self.client.post(reverse("bookings:create_request", args=[self.property.pk]), self.form_data())
        self.assertRedirects(response, reverse("bookings:my_requests"))
        rental_request = RentalRequest.objects.get(tenant=self.tenant, property=self.property)
        self.assertEqual(rental_request.duration_months, 6)
        self.assertEqual(rental_request.end_date(), lease_end_date(self.move_in, 6))

    def test_invalid_duration_does_not_create_request(self):
        self.client.force_login(self.tenant)
        response = self.client.post(
            reverse("bookings:create_request", args=[self.property.pk]), self.form_data(duration_months=0)
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RentalRequest.objects.exists())

    def test_request_form_page_shows_duration_field(self):
        self.client.force_login(self.tenant)
        response = self.client.get(reverse("bookings:create_request", args=[self.property.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rental duration (months)")

    def test_owner_is_told_the_duration(self):
        self.client.force_login(self.tenant)
        self.client.post(reverse("bookings:create_request", args=[self.property.pk]), self.form_data())
        self.assertTrue(any("6 months" in message.body for message in mail.outbox))


class BookingDurationTests(RentalDurationTestBase):
    def test_approval_copies_duration_to_booking(self):
        rental_request = self.make_request(duration_months=12)
        self.client.force_login(self.owner)
        response = self.client.post(reverse("bookings:approve_request", args=[rental_request.pk]))
        self.assertRedirects(response, reverse("bookings:owner_requests"))
        booking = Booking.objects.get(rental_request=rental_request)
        self.assertEqual(booking.duration_months, 12)
        self.assertEqual(booking.start_date, self.move_in)
        self.assertEqual(booking.end_date(), lease_end_date(self.move_in, 12))
        self.assertTrue(any("1 year" in message.body for message in mail.outbox))

    def test_existing_records_default_to_one_month(self):
        # Rows created before the duration feature (see migration 0002) get 1 month.
        self.assertEqual(Booking._meta.get_field("duration_months").default, 1)
        self.assertEqual(RentalRequest._meta.get_field("duration_months").default, 1)


class DurationPagesTests(RentalDurationTestBase):
    def setUp(self):
        super().setUp()
        self.rental_request = self.make_request(duration_months=6)

    def test_tenant_my_requests_shows_duration(self):
        self.client.force_login(self.tenant)
        response = self.client.get(reverse("bookings:my_requests"))
        self.assertContains(response, "6 months")

    def test_owner_requests_shows_duration(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("bookings:owner_requests"))
        self.assertContains(response, "6 months")

    def test_my_bookings_and_payment_show_duration(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("bookings:approve_request", args=[self.rental_request.pk]))
        booking = Booking.objects.get(rental_request=self.rental_request)

        self.client.force_login(self.tenant)
        response = self.client.get(reverse("bookings:my_bookings"))
        self.assertContains(response, "6 months")
        response = self.client.get(reverse("payments:make_payment", args=[booking.pk]))
        self.assertContains(response, "6 months")
