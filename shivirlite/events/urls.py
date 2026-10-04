from django.urls import path

from .views import (
    EventAttendanceAPIView,
    EventDetailAPIView,
    EventListCreateAPIView,
    EventRegisterAPIView,
    EventRegistrationsAPIView,
    EventSummaryAPIView,
    RegistrationTransferAPIView,
)

urlpatterns = [
    path(
        'events/',
        EventListCreateAPIView.as_view(),
        name='event-list-create',
    ),
    path(
        'events/<uuid:pk>/',
        EventDetailAPIView.as_view(),
        name='event-detail',
    ),
    path(
        'events/<uuid:event_id>/register/',
        EventRegisterAPIView.as_view(),
        name='event-register',
    ),
    path(
        'events/<uuid:event_id>/attendance/',
        EventAttendanceAPIView.as_view(),
        name='event-attendance',
    ),
    path(
        'events/<uuid:event_id>/registrations/',
        EventRegistrationsAPIView.as_view(),
        name='event-registrations',
    ),
    path(
        'events/<uuid:event_id>/summary/',
        EventSummaryAPIView.as_view(),
        name='event-summary',
    ),
    path(
        'registrations/<uuid:pk>/transfer/',
        RegistrationTransferAPIView.as_view(),
        name='registration-transfer',
    ),
]
