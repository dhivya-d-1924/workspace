"""
Creates (or updates) an admin account from environment variables, so an
admin login always exists after deploy without needing shell access.

Reads:
  DJANGO_SUPERUSER_USERNAME
  DJANGO_SUPERUSER_EMAIL
  DJANGO_SUPERUSER_PASSWORD

Safe to run on every deploy: if the user already exists, it just makes
sure the password/flags/role are correct rather than erroring out (unlike
Django's built-in `createsuperuser --noinput`, which fails if the user
already exists).

Usage:
    python manage.py ensure_admin
"""
import os

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = "Create or update an admin user from DJANGO_SUPERUSER_* environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not all([username, email, password]):
            self.stdout.write(self.style.WARNING(
                "DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD not fully set — skipping admin setup."
            ))
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )
        user.email = email
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.role = "admin"
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} admin user '{username}'."))
