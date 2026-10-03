from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from events.models import Attendance, Event, Participant, Registration


@pytest.fixture
def multi_day_event(db):
    return Event.objects.create(
        title='Three Day Hackathon',
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 12),
        capacity=50,
        fee=Decimal('500.00'),
        is_published=True,
    )


@pytest.fixture
def confirmed_reg(multi_day_event):
    p = Participant.objects.create(
        full_name='Alice Attendee',
        email='alice@example.com',
        phone='+919876543201',
    )
    return Registration.objects.create(
        event=multi_day_event,
        participant=p,
        status=Registration.Status.CONFIRMED,
        amount_paid=multi_day_event.fee,
    )


@pytest.fixture
def cancelled_reg(multi_day_event):
    p = Participant.objects.create(
        full_name='Bob Cancelled',
        email='bob@example.com',
        phone='+919876543202',
    )
    return Registration.objects.create(
        event=multi_day_event,
        participant=p,
        status=Registration.Status.CANCELLED,
        amount_paid=multi_day_event.fee,
    )


@pytest.mark.django_db
class TestAttendance:
    def test_attendance_staff_success(
        self, staff_client, multi_day_event, confirmed_reg
    ):
        payload = {
            'registration_ids': [str(confirmed_reg.id)],
            'date': '2026-11-10',
        }
        response = staff_client.post(
            f'/api/events/{multi_day_event.id}/attendance/',
            payload,
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert str(confirmed_reg.id) in response.data['marked']
        assert Attendance.objects.filter(
            registration=confirmed_reg, date=date(2026, 11, 10)
        ).exists()

    def test_attendance_regular_user_forbidden(
        self, regular_client, multi_day_event, confirmed_reg
    ):
        payload = {
            'registration_ids': [str(confirmed_reg.id)],
            'date': '2026-11-10',
        }
        response = regular_client.post(
            f'/api/events/{multi_day_event.id}/attendance/',
            payload,
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_attendance_date_before_event_rejected(
        self, staff_client, multi_day_event, confirmed_reg
    ):
        payload = {
            'registration_ids': [str(confirmed_reg.id)],
            'date': '2026-11-09',
        }
        response = staff_client.post(
            f'/api/events/{multi_day_event.id}/attendance/',
            payload,
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_attendance_date_after_event_rejected(
        self, staff_client, multi_day_event, confirmed_reg
    ):
        payload = {
            'registration_ids': [str(confirmed_reg.id)],
            'date': '2026-11-13',
        }
        response = staff_client.post(
            f'/api/events/{multi_day_event.id}/attendance/',
            payload,
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_attendance_non_confirmed_registration_skipped(
        self, staff_client, multi_day_event, cancelled_reg
    ):
        payload = {
            'registration_ids': [str(cancelled_reg.id)],
            'date': '2026-11-10',
        }
        response = staff_client.post(
            f'/api/events/{multi_day_event.id}/attendance/',
            payload,
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['skipped']) == 1
        assert response.data['skipped'][0]['id'] == str(cancelled_reg.id)

    def test_attendance_registration_from_other_event_skipped(
        self, staff_client, multi_day_event
    ):
        other_event = Event.objects.create(
            title='Other Event',
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 12),
            capacity=10,
            fee=Decimal('100.00'),
            is_published=True,
        )
        p = Participant.objects.create(
            full_name='Other Person',
            email='other@example.com',
            phone='+919876543209',
        )
        other_reg = Registration.objects.create(
            event=other_event,
            participant=p,
            status=Registration.Status.CONFIRMED,
            amount_paid=other_event.fee,
        )
        payload = {
            'registration_ids': [str(other_reg.id)],
            'date': '2026-11-10',
        }
        response = staff_client.post(
            f'/api/events/{multi_day_event.id}/attendance/',
            payload,
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['skipped']) == 1
        assert response.data['skipped'][0]['id'] == str(other_reg.id)

    def test_attendance_unknown_registration_id_skipped(
        self, staff_client, multi_day_event
    ):
        fake_id = 999999
        payload = {
            'registration_ids': [fake_id],
            'date': '2026-11-10',
        }
        response = staff_client.post(
            f'/api/events/{multi_day_event.id}/attendance/',
            payload,
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['skipped']) == 1
        assert response.data['skipped'][0]['id'] == str(fake_id)

    def test_attendance_idempotency_same_day_twice(
        self, staff_client, multi_day_event, confirmed_reg
    ):
        payload = {
            'registration_ids': [str(confirmed_reg.id)],
            'date': '2026-11-10',
        }
        resp1 = staff_client.post(
            f'/api/events/{multi_day_event.id}/attendance/',
            payload,
            format='json',
        )
        assert resp1.status_code == status.HTTP_200_OK
        assert str(confirmed_reg.id) in resp1.data['marked']

        # Second attempt on same day
        resp2 = staff_client.post(
            f'/api/events/{multi_day_event.id}/attendance/',
            payload,
            format='json',
        )
        assert resp2.status_code == status.HTTP_200_OK
        assert str(confirmed_reg.id) in resp2.data['already_marked']
        assert Attendance.objects.filter(
            registration=confirmed_reg, date=date(2026, 11, 10)
        ).count() == 1

    def test_attendance_different_dates_create_different_rows(
        self, staff_client, multi_day_event, confirmed_reg
    ):
        resp1 = staff_client.post(
            f'/api/events/{multi_day_event.id}/attendance/',
            {'registration_ids': [str(confirmed_reg.id)], 'date': '2026-11-10'},
            format='json',
        )
        assert resp1.status_code == status.HTTP_200_OK

        resp2 = staff_client.post(
            f'/api/events/{multi_day_event.id}/attendance/',
            {'registration_ids': [str(confirmed_reg.id)], 'date': '2026-11-11'},
            format='json',
        )
        assert resp2.status_code == status.HTTP_200_OK

        assert Attendance.objects.filter(registration=confirmed_reg).count() == 2
