from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from events.models import Event


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user(db):
    user = get_user_model().objects.create_user(
        username='staff',
        password='StaffPassword123!',
        email='staff@example.com',
        is_staff=True,
        is_superuser=True,
    )
    return user


@pytest.fixture
def regular_user(db):
    user = get_user_model().objects.create_user(
        username='regular',
        password='RegularPassword123!',
        email='regular@example.com',
        is_staff=False,
    )
    return user


@pytest.fixture
def staff_token(staff_user):
    token, _ = Token.objects.get_or_create(user=staff_user)
    return token


@pytest.fixture
def regular_token(regular_user):
    token, _ = Token.objects.get_or_create(user=regular_user)
    return token


@pytest.fixture
def staff_client(api_client, staff_token):
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {staff_token.key}')
    return api_client


@pytest.fixture
def regular_client(api_client, regular_token):
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {regular_token.key}')
    return api_client


@pytest.fixture
def sample_published_event(db):
    return Event.objects.create(
        title='Django Masterclass',
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 12),
        capacity=30,
        fee=Decimal('1500.00'),
        is_published=True,
    )


@pytest.fixture
def sample_unpublished_event(db):
    return Event.objects.create(
        title='Internal Staff Sync',
        start_date=date(2026, 11, 15),
        end_date=date(2026, 11, 16),
        capacity=10,
        fee=Decimal('0.00'),
        is_published=False,
    )
