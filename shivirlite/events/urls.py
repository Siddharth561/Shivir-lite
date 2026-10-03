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
        'events/<int:pk>/',
        EventDetailAPIView.as_view(),
        name='event-detail',
    ),
    path(
        'events/<int:event_id>/register/',
        EventRegisterAPIView.as_view(),
        name='event-register',
    ),
    path(
        'events/<int:event_id>/attendance/',
        EventAttendanceAPIView.as_view(),
        name='event-attendance',
    ),
    path(
        'events/<int:event_id>/registrations/',
        EventRegistrationsAPIView.as_view(),
        name='event-registrations',
    ),
    path(
        'events/<int:event_id>/summary/',
        EventSummaryAPIView.as_view(),
        name='event-summary',
    ),
    path(
        'registrations/<int:pk>/transfer/',
        RegistrationTransferAPIView.as_view(),
        name='registration-transfer',
    ),
]
