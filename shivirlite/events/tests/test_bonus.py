from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from rest_framework import status

from events.models import Attendance, Event, Participant, Registration


@pytest.fixture
def source_event(db):
    return Event.objects.create(
        title='Source Event',
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 12),
        capacity=10,
        fee=Decimal('1000.00'),
        is_published=True,
    )


@pytest.fixture
def target_event(db):
    return Event.objects.create(
        title='Target Event',
        start_date=date(2026, 11, 15),
        end_date=date(2026, 11, 20),
        capacity=10,
        fee=Decimal('1500.00'),
        is_published=True,
    )


@pytest.fixture
def participant(db):
    return Participant.objects.create(
        full_name='Test Transfer User',
        email='transfer@example.com',
        phone='+919998887770',
    )


@pytest.fixture
def confirmed_registration(source_event, participant):
    return Registration.objects.create(
        event=source_event,
        participant=participant,
        status=Registration.Status.CONFIRMED,
        amount_paid=source_event.fee,
    )


@pytest.mark.django_db
class TestFieldSelection:
    def test_field_selection_returns_only_requested_fields(self, staff_client, source_event):
        response = staff_client.get('/api/events/?fields=id,title')
        assert response.status_code == status.HTTP_200_OK
        data = response.data.get('results', response.data)
        assert len(data) >= 1
        item = data[0]
        assert set(item.keys()) == {'id', 'title'}


@pytest.mark.django_db
class TestRegistrationTransfer:
    def test_transfer_registration_success(self, staff_client, confirmed_registration, target_event):
        # Attach attendance to registration on source event
        Attendance.objects.create(
            registration=confirmed_registration,
            date=date(2026, 11, 10),
        )

        response = staff_client.post(
            f'/api/registrations/{confirmed_registration.id}/transfer/',
            {'target_event_id': target_event.id},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

        confirmed_registration.refresh_from_db()
        assert confirmed_registration.event == target_event
        assert confirmed_registration.amount_paid == target_event.fee

        # Verify attendance row still exists attached to the registration
        assert Attendance.objects.filter(registration=confirmed_registration).count() == 1

    def test_transfer_to_unpublished_event_fails(self, staff_client, confirmed_registration, target_event):
        target_event.is_published = False
        target_event.save()

        response = staff_client.post(
            f'/api/registrations/{confirmed_registration.id}/transfer/',
            {'target_event_id': target_event.id},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_transfer_to_full_event_fails(self, staff_client, confirmed_registration, target_event):
        target_event.capacity = 1
        target_event.save()

        other_participant = Participant.objects.create(
            full_name='Other Person',
            email='other@example.com',
            phone='+919998887771',
        )
        Registration.objects.create(
            event=target_event,
            participant=other_participant,
            status=Registration.Status.CONFIRMED,
            amount_paid=target_event.fee,
        )

        response = staff_client.post(
            f'/api/registrations/{confirmed_registration.id}/transfer/',
            {'target_event_id': target_event.id},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUnpublishEndedEventsCommand:
    def test_unpublish_ended_events_idempotent(self):
        past_event = Event.objects.create(
            title='Old Past Event',
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 5),
            capacity=10,
            fee=Decimal('0.00'),
            is_published=True,
        )
        future_event = Event.objects.create(
            title='Future Event',
            start_date=date(2028, 1, 1),
            end_date=date(2028, 1, 5),
            capacity=10,
            fee=Decimal('0.00'),
            is_published=True,
        )

        # First run
        call_command('unpublish_ended_events')
        past_event.refresh_from_db()
        future_event.refresh_from_db()

        assert past_event.is_published is False
        assert future_event.is_published is True

        # Second run (idempotency check)
        call_command('unpublish_ended_events')
        past_event.refresh_from_db()
        future_event.refresh_from_db()

        assert past_event.is_published is False
        assert future_event.is_published is True
