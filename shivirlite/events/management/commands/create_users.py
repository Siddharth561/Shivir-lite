from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = 'Create one staff user and one regular user and print their tokens.'

    def handle(self, *args, **options):
        user_model = get_user_model()
        users = (
            ('staff', 'StaffPass123!', True),
            ('regular', 'UserPass123!', False),
        )
        for username, password, is_staff in users:
            user, _ = user_model.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'is_staff': is_staff,
                },
            )
            user.set_password(password)
            user.is_staff = is_staff
            user.is_superuser = is_staff
            user.save()
            token, _ = Token.objects.get_or_create(user=user)
            self.stdout.write(
                f'{username}: username={username} token={token.key}'
            )
