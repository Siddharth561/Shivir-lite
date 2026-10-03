from django.db.models import Count
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import filter_events
from .models import Event, Registration
from .serializers import (
    AttendanceRequestSerializer,
    EventSerializer,
    RegistrationAdminSerializer,
    RegistrationPublicSerializer,
    RegistrationRequestSerializer,
)
from .services import event_summary, mark_attendance, register_for_event


class EventListCreateAPIView(APIView):
    """
    List events (GET) with staff filtering, date filtering, and pagination.
    Create a new event (POST) - Staff only.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            queryset = Event.objects.all()
        else:
            queryset = Event.objects.filter(is_published=True)

        queryset = filter_events(queryset, request.query_params)
        queryset = queryset.order_by('start_date', 'title')

        fields_param = request.query_params.get('fields')
        fields = [f.strip() for f in fields_param.split(',') if f.strip()] if fields_param else None

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = EventSerializer(page, many=True, fields=fields)
            return paginator.get_paginated_response(serializer.data)

        serializer = EventSerializer(queryset, many=True, fields=fields)
        return Response(serializer.data)

    def post(self, request):
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only staff users can create events.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EventDetailAPIView(APIView):
    """
    Retrieve an event (GET) - regular users see only published events.
    Update full (PUT) - Staff only.
    Update partial (PATCH) - Staff only.
    Delete (DELETE) - Staff only.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            event = Event.objects.get(pk=pk)
        except (Event.DoesNotExist, ValueError):
            raise NotFound('Event not found.')

        if not user.is_staff and not event.is_published:
            raise NotFound('Event not found.')

        return event

    def get(self, request, pk):
        event = self.get_object(pk, request.user)
        serializer = EventSerializer(event)
        return Response(serializer.data)

    def put(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only staff users can update events.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        event = self.get_object(pk, request.user)
        serializer = EventSerializer(event, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only staff users can update events.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        event = self.get_object(pk, request.user)
        serializer = EventSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only staff users can delete events.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        event = self.get_object(pk, request.user)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventRegisterAPIView(APIView):
    """
    Register a participant for an event (POST).
    Authenticated users only.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        try:
            event = Event.objects.get(pk=event_id)
        except (Event.DoesNotExist, ValueError):
            raise NotFound('Event not found.')

        serializer = RegistrationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = register_for_event(event.pk, serializer.validated_data)
        return Response(
            RegistrationPublicSerializer(registration).data,
            status=status.HTTP_201_CREATED,
        )


class EventAttendanceAPIView(APIView):
    """
    Mark attendance for an event (POST) - Staff only.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only staff users can mark attendance.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            event = Event.objects.get(pk=event_id)
        except (Event.DoesNotExist, ValueError):
            raise NotFound('Event not found.')

        serializer = AttendanceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = mark_attendance(
            event,
            serializer.validated_data['registration_ids'],
            serializer.validated_data['date'],
            request.user,
        )
        return Response(result, status=status.HTTP_200_OK)


class EventRegistrationsAPIView(APIView):
    """
    List all registrations for an event (GET) - Staff only.
    Optimized query avoiding N+1 via select_related and annotate.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only staff users can view registrations.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            event = Event.objects.get(pk=event_id)
        except (Event.DoesNotExist, ValueError):
            raise NotFound('Event not found.')

        registrations = (
            Registration.objects.filter(event=event)
            .select_related('participant')
            .annotate(days_attended=Count('attendances'))
            .order_by('-created_at')
        )
        return Response(
            RegistrationAdminSerializer(registrations, many=True).data
        )


class EventSummaryAPIView(APIView):
    """
    Get aggregated summary statistics for an event (GET) - Staff only.
    Uses database aggregation without Python loops.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only staff users can view event summaries.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            event = Event.objects.get(pk=event_id)
        except (Event.DoesNotExist, ValueError):
            raise NotFound('Event not found.')

        summary = event_summary(event)
        return Response(summary, status=status.HTTP_200_OK)


class RegistrationTransferAPIView(APIView):
    """
    POST /api/registrations/{id}/transfer/
    Transfer a registration to another event.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from .serializers import RegistrationTransferSerializer
        from .services import transfer_registration

        serializer = RegistrationTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_event_id = serializer.validated_data['target_event_id']
        registration = transfer_registration(pk, target_event_id)
        return Response(
            RegistrationPublicSerializer(registration).data,
            status=status.HTTP_200_OK,
        )

