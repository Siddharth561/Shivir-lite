from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from events.models import Attendance, Event, Participant, Registration


@pytest.fixture
def event_with_registrations(db):
    event = Event.objects.create(
        title='Query Optimization Event',
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 15),
        capacity=1000,
        fee=Decimal('100.00'),
        is_published=True,
    )
    return event


@pytest.mark.django_db
class TestRegistrationsList:
    def test_staff_can_retrieve_registrations(
        self, staff_client, event_with_registrations
    ):
        p = Participant.objects.create(
            full_name='Test Participant',
            email='test@example.com',
            phone='+919876543210',
        )
        reg = Registration.objects.create(
            event=event_with_registrations,
            participant=p,
            status=Registration.Status.CONFIRMED,
            amount_paid=Decimal('100.00'),
            admin_note='VIP Participant',
        )
        Attendance.objects.create(
            registration=reg,
            date=date(2026, 11, 10),
        )
        Attendance.objects.create(
            registration=reg,
            date=date(2026, 11, 11),
        )

        response = staff_client.get(
            f'/api/events/{event_with_registrations.id}/registrations/'
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert len(data) == 1
        item = data[0]
        assert item['participant_name'] == 'Test Participant'
        assert item['participant_phone'] == '+919876543210'
        assert item['admin_note'] == 'VIP Participant'
        assert item['days_attended'] == 2

    def test_regular_user_forbidden(
        self, regular_client, event_with_registrations
    ):
        response = regular_client.get(
            f'/api/events/{event_with_registrations.id}/registrations/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_query_count_remains_constant(
        self, staff_client, django_assert_num_queries
    ):
        """
        Verify no N+1 query issue: query count is identical regardless of registration count.
        """
        # Event 1 with 5 registrations
        event1 = Event.objects.create(
            title='Small Event',
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 12),
            capacity=100,
            fee=Decimal('50.00'),
            is_published=True,
        )
        for i in range(5):
            p = Participant.objects.create(
                full_name=f'Person {i}',
                email=f'person_{i}@example.com',
                phone=f'+9190000000{i:02d}',
            )
            reg = Registration.objects.create(
                event=event1,
                participant=p,
                status=Registration.Status.CONFIRMED,
                amount_paid=Decimal('50.00'),
            )
            Attendance.objects.create(registration=reg, date=date(2026, 11, 10))

        # Event 2 with 30 registrations
        event2 = Event.objects.create(
            title='Larger Event',
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 12),
            capacity=100,
            fee=Decimal('50.00'),
            is_published=True,
        )
        for i in range(30):
            p = Participant.objects.create(
                full_name=f'Big Person {i}',
                email=f'big_person_{i}@example.com',
                phone=f'+9191000000{i:02d}',
            )
            reg = Registration.objects.create(
                event=event2,
                participant=p,
                status=Registration.Status.CONFIRMED,
                amount_paid=Decimal('50.00'),
            )
            Attendance.objects.create(registration=reg, date=date(2026, 11, 10))

        # Measure queries for event 1 (5 items)
        with django_assert_num_queries(3):
            # 1 for auth user/token check, 1 for event check, 1 for registrations query with select_related & annotate
            resp1 = staff_client.get(f'/api/events/{event1.id}/registrations/')
            assert resp1.status_code == status.HTTP_200_OK

        # Measure queries for event 2 (30 items) - MUST BE EXACTLY SAME QUERY COUNT (3)
        with django_assert_num_queries(3):
            resp2 = staff_client.get(f'/api/events/{event2.id}/registrations/')
            assert resp2.status_code == status.HTTP_200_OK
