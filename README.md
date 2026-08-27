# Rental Property Management Platform 

A Django-based rental property management platform with Admin, Property Owner, Tenant, and Technician roles.

## Features

- Role-based authentication and authorization
- Owner property/room/image/amenity management
- Tenant property discovery, search, and filters
- Rental requests and owner approval/rejection
- Booking management
- Mock payments with transaction history
- Maintenance ticket workflow: Open → Assigned → In Progress → Resolved → Closed
- Technician assignment and technician dashboard
- Property reporting and admin review
- Email notifications using Django's console email backend
- Bootstrap responsive UI
- Form validation, CSRF protection, access control, and automated tests
- Custom 403/404/500 pages

## Project apps

- `accounts` — authentication, profiles, roles
- `properties` — properties, rooms, images, amenities
- `bookings` — rental requests and bookings
- `payments` — mock payments
- `maintenance` — technicians and maintenance tickets
- `core` — home page, admin dashboard, property reports

## Setup

```bash
python -m venv venv
venv\\Scripts\\activate       # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Verification

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

`run_checks.py` can also be used as a convenience wrapper.

## Development email

The project uses Django's console email backend. During development, email messages are printed in the terminal rather than sent externally.

## Mock payments

No real money is processed. Card/CVV values are used for mock validation only. Full card numbers and CVV values are not stored; successful card payments retain only the last four digits.
