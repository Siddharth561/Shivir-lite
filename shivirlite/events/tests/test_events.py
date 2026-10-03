from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from events.models import Event


@pytest.mark.django_db
class TestEventList:
    def test_get_list_unauthenticated(self, api_client):
        response = api_client.get('/api/events/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_list_regular_sees_only_published(
        self, regular_client, sample_published_event, sample_unpublished_event
    ):
        response = regular_client.get('/api/events/')
        assert response.status_code == status.HTTP_200_OK
        data = response.data.get('results', response.data)
        ids = [item['id'] for item in data]
        assert sample_published_event.id in ids
        assert sample_unpublished_event.id not in ids

    def test_get_list_staff_sees_all(
        self, staff_client, sample_published_event, sample_unpublished_event
    ):
        response = staff_client.get('/api/events/')
        assert response.status_code == status.HTTP_200_OK
        data = response.data.get('results', response.data)
        ids = [item['id'] for item in data]
        assert sample_published_event.id in ids
        assert sample_unpublished_event.id in ids

    def test_filter_is_published_true(
        self, staff_client, sample_published_event, sample_unpublished_event
    ):
        response = staff_client.get('/api/events/?is_published=true')
        assert response.status_code == status.HTTP_200_OK
        data = response.data.get('results', response.data)
        assert all(item['is_published'] is True for item in data)
        ids = [item['id'] for item in data]
        assert sample_published_event.id in ids
        assert sample_unpublished_event.id not in ids

    def test_filter_is_published_false(
        self, staff_client, sample_published_event, sample_unpublished_event
    ):
        response = staff_client.get('/api/events/?is_published=false')
        assert response.status_code == status.HTTP_200_OK
        data = response.data.get('results', response.data)
        assert all(item['is_published'] is False for item in data)
        ids = [item['id'] for item in data]
        assert sample_unpublished_event.id in ids
        assert sample_published_event.id not in ids

    def test_filter_is_published_invalid(self, staff_client):
        response = staff_client.get('/api/events/?is_published=maybe')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_start_date_after(self, staff_client):
        e1 = Event.objects.create(
            title='Early Event',
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
            capacity=10,
            fee=Decimal('100.00'),
            is_published=True,
        )
        e2 = Event.objects.create(
            title='Late Event',
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 3),
            capacity=10,
            fee=Decimal('100.00'),
            is_published=True,
        )
        response = staff_client.get('/api/events/?start_date_after=2026-11-01')
        assert response.status_code == status.HTTP_200_OK
        data = response.data.get('results', response.data)
        ids = [item['id'] for item in data]
        assert e2.id in ids
        assert e1.id not in ids

    def test_filter_start_date_after_invalid(self, staff_client):
        response = staff_client.get('/api/events/?start_date_after=not-a-date')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_pagination_page_size_20(self, staff_client):
        for i in range(25):
            Event.objects.create(
                title=f'Batch Event {i:02d}',
                start_date=date(2026, 10, 1),
                end_date=date(2026, 10, 2),
                capacity=10,
                fee=Decimal('50.00'),
                is_published=True,
            )
        response = staff_client.get('/api/events/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) == 20
        assert response.data['count'] >= 25


@pytest.mark.django_db
class TestEventCreate:
    def test_create_event_staff_success(self, staff_client):
        payload = {
            'title': 'Python Backend Workshop',
            'start_date': '2026-11-10',
            'end_date': '2026-11-12',
            'capacity': 50,
            'fee': '1500.00',
            'is_published': True,
        }
        response = staff_client.post('/api/events/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Python Backend Workshop'
        assert response.data['capacity'] == 50
        assert Event.objects.filter(title='Python Backend Workshop').exists()

    def test_create_event_regular_user_forbidden(self, regular_client):
        payload = {
            'title': 'Unauthorized Workshop',
            'start_date': '2026-11-10',
            'end_date': '2026-11-12',
            'capacity': 50,
            'fee': '1500.00',
            'is_published': True,
        }
        response = regular_client.post('/api/events/', payload, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_event_zero_capacity_rejected(self, staff_client):
        payload = {
            'title': 'Zero Capacity Event',
            'start_date': '2026-11-10',
            'end_date': '2026-11-12',
            'capacity': 0,
            'fee': '500.00',
            'is_published': True,
        }
        response = staff_client.post('/api/events/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_event_negative_capacity_rejected(self, staff_client):
        payload = {
            'title': 'Negative Capacity Event',
            'start_date': '2026-11-10',
            'end_date': '2026-11-12',
            'capacity': -5,
            'fee': '500.00',
            'is_published': True,
        }
        response = staff_client.post('/api/events/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_event_end_date_before_start_date_rejected(self, staff_client):
        payload = {
            'title': 'Backward Event',
            'start_date': '2026-11-12',
            'end_date': '2026-11-10',
            'capacity': 20,
            'fee': '500.00',
            'is_published': True,
        }
        response = staff_client.post('/api/events/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestEventDetail:
    def test_retrieve_published_event_success(
        self, regular_client, sample_published_event
    ):
        response = regular_client.get(f'/api/events/{sample_published_event.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == sample_published_event.id

    def test_retrieve_unpublished_event_regular_404(
        self, regular_client, sample_unpublished_event
    ):
        response = regular_client.get(f'/api/events/{sample_unpublished_event.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_unpublished_event_staff_success(
        self, staff_client, sample_unpublished_event
    ):
        response = staff_client.get(f'/api/events/{sample_unpublished_event.id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_non_existing_event_404(self, staff_client):
        random_id = 999999
        response = staff_client.get(f'/api/events/{random_id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_update_staff_success(
        self, staff_client, sample_published_event
    ):
        payload = {
            'title': 'Updated Masterclass',
            'start_date': '2026-11-10',
            'end_date': '2026-11-14',
            'capacity': 45,
            'fee': '2000.00',
            'is_published': True,
        }
        response = staff_client.put(
            f'/api/events/{sample_published_event.id}/', payload, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        sample_published_event.refresh_from_db()
        assert sample_published_event.title == 'Updated Masterclass'
        assert sample_published_event.capacity == 45

    def test_put_update_regular_user_forbidden(
        self, regular_client, sample_published_event
    ):
        payload = {
            'title': 'Hacked Title',
            'start_date': '2026-11-10',
            'end_date': '2026-11-14',
            'capacity': 45,
            'fee': '2000.00',
            'is_published': True,
        }
        response = regular_client.put(
            f'/api/events/{sample_published_event.id}/', payload, format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_patch_partial_update_staff_success(
        self, staff_client, sample_published_event
    ):
        payload = {'capacity': 60}
        response = staff_client.patch(
            f'/api/events/{sample_published_event.id}/', payload, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        sample_published_event.refresh_from_db()
        assert sample_published_event.capacity == 60

    def test_patch_regular_user_forbidden(
        self, regular_client, sample_published_event
    ):
        payload = {'capacity': 999}
        response = regular_client.patch(
            f'/api/events/{sample_published_event.id}/', payload, format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_staff_success(
        self, staff_client, sample_published_event
    ):
        response = staff_client.delete(f'/api/events/{sample_published_event.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Event.objects.filter(id=sample_published_event.id).exists()

    def test_delete_regular_user_forbidden(
        self, regular_client, sample_published_event
    ):
        response = regular_client.delete(f'/api/events/{sample_published_event.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
