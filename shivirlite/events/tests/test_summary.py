from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from events.models import Attendance, Event, Participant, Registration


@pytest.fixture
def summary_event(db):
    # 3-day event: Nov 10, Nov 11, Nov 12
    return Event.objects.create(
        title='Data Science Bootcamp',
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 12),
        capacity=50,
        fee=Decimal('1500.00'),
        is_published=True,
    )


@pytest.mark.django_db
class TestEventSummary:
    def test_summary_regular_user_forbidden(
        self, regular_client, summary_event
    ):
        response = regular_client.get(
            f'/api/events/{summary_event.id}/summary/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_summary_aggregation_metrics(
        self, staff_client, summary_event
    ):
        # Participant 1: Confirmed, attended all 3 days
        p1 = Participant.objects.create(
            full_name='P1 Full Attendance',
            email='p1@example.com',
            phone='+919876543001',
        )
        reg1 = Registration.objects.create(
            event=summary_event,
            participant=p1,
            status=Registration.Status.CONFIRMED,
            amount_paid=Decimal('1500.00'),
        )
        Attendance.objects.create(registration=reg1, date=date(2026, 11, 10))
        Attendance.objects.create(registration=reg1, date=date(2026, 11, 11))
        Attendance.objects.create(registration=reg1, date=date(2026, 11, 12))

        # Participant 2: Confirmed, attended 1 day
        p2 = Participant.objects.create(
            full_name='P2 Partial Attendance',
            email='p2@example.com',
            phone='+919876543002',
        )
        reg2 = Registration.objects.create(
            event=summary_event,
            participant=p2,
            status=Registration.Status.CONFIRMED,
            amount_paid=Decimal('1500.00'),
        )
        Attendance.objects.create(registration=reg2, date=date(2026, 11, 10))

        # Participant 3: Confirmed, attended 0 days
        p3 = Participant.objects.create(
            full_name='P3 No Attendance',
            email='p3@example.com',
            phone='+919876543003',
        )
        Registration.objects.create(
            event=summary_event,
            participant=p3,
            status=Registration.Status.CONFIRMED,
            amount_paid=Decimal('1500.00'),
        )

        # Participant 4: Cancelled registration
        p4 = Participant.objects.create(
            full_name='P4 Cancelled',
            email='p4@example.com',
            phone='+919876543004',
        )
        Registration.objects.create(
            event=summary_event,
            participant=p4,
            status=Registration.Status.CANCELLED,
            amount_paid=Decimal('1500.00'),
        )

        response = staff_client.get(
            f'/api/events/{summary_event.id}/summary/'
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # 3 confirmed
        assert data['registered'] == 3
        # 1 cancelled
        assert data['cancelled'] == 1
        # p1 (3 days) and p2 (1 day) -> 2 attended at least once
        assert data['attended_at_least_once'] == 2
        # p1 only attended all 3 days -> 1
        assert data['attended_every_day'] == 1
        # 3 * 1500 = 4500.00
        assert data['revenue'] == '4500.00'

    def test_empty_event_summary(self, staff_client, summary_event):
        response = staff_client.get(
            f'/api/events/{summary_event.id}/summary/'
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data['registered'] == 0
        assert data['cancelled'] == 0
        assert data['attended_at_least_once'] == 0
        assert data['attended_every_day'] == 0
        assert data['revenue'] == '0.00'
