import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create the configured demo superuser once, without resetting existing credentials.'

    def handle(self, *args, **options):
        del args, options
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
        values = (username, email, password)

        if not any(values):
            self.stdout.write('Demo superuser credentials are not configured; skipping.')
            return
        if not all(values):
            raise CommandError(
                'Set DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, '
                'and DJANGO_SUPERUSER_PASSWORD together.'
            )

        user_model = get_user_model()
        existing_user = user_model.objects.filter(username=username).first()
        if existing_user:
            if not existing_user.is_superuser:
                raise CommandError(
                    f'The configured username {username!r} already belongs to a non-superuser.'
                )
            self.stdout.write(f'Demo superuser {username!r} already exists; leaving it unchanged.')
            return

        validate_password(password)
        user_model.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f'Created demo superuser {username!r}.'))
