from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Participant(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=16, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        self.email = self.email.casefold()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class Event(models.Model):
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    capacity = models.PositiveIntegerField()
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # INR
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'id']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F('start_date')),
                name='check_event_end_date_gte_start_date'
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gt=0),
                name='check_event_capacity_gt_zero'
            ),
        ]

    def __str__(self):
        return self.title


class Registration(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    participant = models.ForeignKey(
        Participant,
        on_delete=models.PROTECT,
        related_name='registrations'
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED
    )
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    admin_note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['participant', 'event'],
                condition=models.Q(status='CONFIRMED'),
                name='unique_confirmed_registration_per_participant_event'
            )
        ]

    def __str__(self):
        return f"{self.participant.full_name} -> {self.event.title} ({self.status})"


class Attendance(models.Model):
    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField()
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendances'
    )
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-marked_at']
        constraints = [
            models.UniqueConstraint(
                fields=['registration', 'date'],
                name='unique_attendance_per_registration_per_day'
            )
        ]

    def __str__(self):
        return f"Attendance {self.registration_id} on {self.date}"
