from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import Event


class Command(BaseCommand):
    help = 'Sets is_published=False on all events whose end_date is in the past.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        updated_count = Event.objects.filter(
            end_date__lt=today,
            is_published=True,
        ).update(is_published=False)
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully unpublished {updated_count} ended events.'
            )
        )
