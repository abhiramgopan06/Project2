# Step 10 — Final Integration & Testing Checklist

This project is the final integrated Django version of the Rental Property Management Platform.

## End-to-end workflows

1. Register as Tenant or Property Owner.
2. Log in and verify role-based dashboard routing.
3. Owner creates a property, rooms, amenities, and images.
4. Tenant searches and filters available properties.
5. Tenant opens a property and submits a rental request.
6. Owner approves/rejects the request.
7. Approval creates a confirmed booking and updates availability.
8. Tenant makes a mock payment and views the transaction history.
9. Tenant creates a maintenance ticket from a confirmed booking.
10. Owner assigns a technician.
11. Technician changes the ticket to In Progress and Resolved.
12. Owner closes the resolved ticket.
13. Users can report problematic properties.
14. Admin reviews reports and monitors platform activity.
15. Email notifications are emitted through Django's development console backend.

## Security checks

- CSRF protection is enabled.
- Logout is POST-only.
- Owner CRUD is restricted to the property's owner.
- Tenant booking/payment/maintenance data is scoped to the logged-in tenant.
- Technician actions are restricted to tickets assigned to that technician.
- Admin-only report/dashboard actions are protected.
- Uploaded media is served only through Django's development media configuration.
- Payment CVV/card number is not persisted; card payments retain only the last four digits.

## Commands

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py collectstatic --noinput
```

## Verified status

All four commands above were re-run before this package was finalized:

- `check` — System check identified no issues.
- `makemigrations --check --dry-run` — No changes detected (migrations are up to date).
- `test` — 8/8 tests pass.
- `collectstatic` — completes cleanly.

For local development:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
