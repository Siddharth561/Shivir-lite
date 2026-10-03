from rest_framework import serializers

from .models import Attendance, Event, Registration
from .utils.phone import normalize_phone


class EventSerializer(serializers.ModelSerializer):
    capacity = serializers.IntegerField()

    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'start_date',
            'end_date',
            'capacity',
            'fee',
            'is_published',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)
        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'capacity must be greater than 0.'
            )
        return value

    def validate(self, attrs):
        start_date = attrs.get(
            'start_date',
            self.instance.start_date if self.instance else None,
        )
        end_date = attrs.get(
            'end_date',
            self.instance.end_date if self.instance else None,
        )
        if start_date is not None and end_date is not None and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': 'end_date cannot be before start_date.'
            })
        return attrs


class RegistrationRequestSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=64)

    def validate_email(self, value):
        return value.casefold()

    def validate_phone(self, value):
        try:
            return normalize_phone(value)
        except ValueError as error:
            raise serializers.ValidationError(
                'Enter a valid phone number.'
            ) from error


RegisterSerializer = RegistrationRequestSerializer


class RegistrationPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = ['id', 'status', 'amount_paid', 'created_at']
        read_only_fields = fields


RegistrationSerializer = RegistrationPublicSerializer


class AttendanceRequestSerializer(serializers.Serializer):
    registration_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )
    date = serializers.DateField()


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ['id', 'registration', 'date', 'marked_by', 'marked_at']
        read_only_fields = fields


class RegistrationAdminSerializer(serializers.ModelSerializer):
    participant_name = serializers.CharField(
        source='participant.full_name',
        read_only=True,
    )
    participant_phone = serializers.CharField(
        source='participant.phone',
        read_only=True,
    )
    days_attended = serializers.IntegerField(read_only=True)

    class Meta:
        model = Registration
        fields = [
            'id',
            'participant_name',
            'participant_phone',
            'status',
            'amount_paid',
            'admin_note',
            'days_attended',
            'created_at',
        ]
        read_only_fields = fields


RegistrationListSerializer = RegistrationAdminSerializer


class EventSummarySerializer(serializers.Serializer):
    registered = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    attended_at_least_once = serializers.IntegerField()
    attended_every_day = serializers.IntegerField()
    revenue = serializers.CharField()


class RegistrationTransferSerializer(serializers.Serializer):
    target_event_id = serializers.IntegerField(required=False)
    event_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        target_id = attrs.get('target_event_id') or attrs.get('event_id')
        if not target_id:
            raise serializers.ValidationError({
                'target_event_id': 'Target event ID is required.'
            })
        attrs['target_event_id'] = target_id
        return attrs

