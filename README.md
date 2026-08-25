# Rental Property Management Platform — Step 1.1 + Step 2

This ZIP contains the Django foundation plus the custom authentication and role system for the Rental Property Management Platform.

## Completed
- Django project and app configuration
- Templates, static files and media/image uploads
- Bootstrap base layout and navigation
- Custom `accounts.User` model
- Admin, Property Owner and Tenant roles
- Owner/Tenant registration
- Login and logout
- Role-based dashboard routing and access checks
- Profile editing and profile image upload
- Console email on successful registration
- Django admin integration
- Custom 403/404/500 templates
- Placeholder URL modules for Properties, Bookings, Payments and Maintenance

## Setup

```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
```

Install:
```bash
pip install -r requirements.txt
```

Database:
```bash
python manage.py makemigrations
python manage.py migrate
```

Create admin:
```bash
python manage.py createsuperuser
```

Run:
```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Main URLs
- `/`
- `/accounts/register/`
- `/accounts/login/`
- `/accounts/dashboard/`
- `/accounts/profile/`
- `/admin/`

## Development email
The project uses Django's console email backend. Registration emails appear in the terminal. Later, this can be switched to SMTP.

## Security note
Change the development `SECRET_KEY` and configure production settings before deployment.

## Step 3 — Property Management

Implemented property management for property owners:

- Property model with owner, title, description, location, address, type, rent and availability
- Amenity many-to-many relationship
- Property image uploads, primary image handling and deletion
- Room management with unique room numbers per property
- Public property listing and detail pages
- Search and filters for location, rent, property type and availability
- Owner-only property CRUD
- Owner room CRUD
- Django admin management for properties, images, rooms and amenities

### Step 3 test

```bash
python manage.py makemigrations properties
python manage.py migrate
python manage.py check
python manage.py runserver
```

Register/login as an Owner, open the Owner Dashboard, then use **Manage Properties**.

## Step 5 - Rental Requests & Bookings
- Tenants can request available properties and optionally select an available room.
- Owners can approve or reject pending requests.
- Approval creates a confirmed Booking automatically.
- Approved room/property availability is updated.
- Tenants can view request and booking status.
- Email notifications are sent through Django's configured development email backend.
