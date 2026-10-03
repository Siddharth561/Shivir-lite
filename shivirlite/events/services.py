from django.db import transaction, IntegrityError
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from .models import Event, Participant, Registration
from .exceptions import DuplicateRegistrationError
from .utils.phone import normalize_phone


@transaction.atomic
def register_participant(event,full_name,email,phone):
    event = Event.objects.select_for_update().get(pk=event.pk)

    if not event.is_published:
        raise ValidationError({"event": "You cannot register for an unpublished event."})
    if timezone.localdate() > event.end_date:
        raise ValidationError({"event": "You cannot register for an event that has ended."})
    normalized_phone = normalize_phone(phone)
    email = email.strip().lower()
    participant = Participant.objects.filter(phone=normalized_phone).first()

    if participant is None:
        participant = Participant.objects.filter(email__iexact=email).first()

    if participant is None:
        participant = Participant.objects.create(full_name=full_name,email=email,phone=normalized_phone)

    existing_registration = (Registration.objects.filter(participant=participant,event=event,status=Registration.Status.CONFIRMED).first())
    if existing_registration:
        raise DuplicateRegistrationError()

    confirmed_count = (Registration.objects.filter(event=event,status=Registration.Status.CONFIRMED).count())

    if confirmed_count >= event.capacity:
        raise ValidationError({"detail": "Event is full."}) 

    try:
        registration = Registration.objects.create(
            participant=participant,
            event=event,
            status=Registration.Status.CONFIRMED,
            amount_paid=event.fee,
        )
    return registration


def transfer_registration(registration_id, target_event_id):
    with transaction.atomic():
        try:
            registration = Registration.objects.select_for_update().select_related('participant', 'event').get(pk=registration_id)
        except (Registration.DoesNotExist, ValueError):
            raise ValidationError({'registration': 'Registration not found.'})

        try:
            target_event = Event.objects.select_for_update().get(pk=target_event_id)
        except (Event.DoesNotExist, ValueError):
            raise ValidationError({'target_event_id': 'Target event not found.'})

        if registration.event_id == target_event.id:
            raise ValidationError({'target_event_id': 'Registration is already for this event.'})

        if registration.status != Registration.Status.CONFIRMED:
            raise ValidationError({'registration': 'Only confirmed registrations can be transferred.'})

        if not target_event.is_published:
            raise ValidationError({'target_event_id': 'Target event is not published.'})

        if target_event.end_date < timezone.localdate():
            raise ValidationError({'target_event_id': 'Target event has ended.'})

        existing_reg = Registration.objects.filter(
            participant=registration.participant,
            event=target_event,
            status=Registration.Status.CONFIRMED,
        ).first()
        if existing_reg:
            raise DuplicateRegistrationError()

        confirmed_count = Registration.objects.filter(
            event=target_event,
            status=Registration.Status.CONFIRMED,
        ).count()
        if confirmed_count >= target_event.capacity:
            raise ValidationError({'detail': 'Target event is full.'})

        registration.event = target_event
        registration.amount_paid = target_event.fee
        registration.save()
        return registration


def mark_attendance(event, registration_ids, attendance_date, marked_by):
    from .models import Attendance
    if not event.start_date <= attendance_date <= event.end_date:
        raise ValidationError({'date': 'Attendance date must be within the event dates.'})

    registration_ids = list(dict.fromkeys(registration_ids))
    with transaction.atomic():
        registrations = {
            registration.pk: registration
            for registration in Registration.objects.select_for_update().filter(
                event=event,
                pk__in=registration_ids,
            )
        }
        confirmed_ids = [
            registration_id
            for registration_id in registration_ids
            if registration_id in registrations
            and registrations[registration_id].status == Registration.Status.CONFIRMED
        ]
        existing_ids = set(Attendance.objects.filter(
            registration_id__in=confirmed_ids,
            date=attendance_date,
        ).values_list('registration_id', flat=True))

        Attendance.objects.bulk_create(
            [
                Attendance(
                    registration_id=registration_id,
                    date=attendance_date,
                    marked_by=marked_by,
                )
                for registration_id in confirmed_ids
                if registration_id not in existing_ids
            ],
            ignore_conflicts=True,
        )

    marked = [
        str(registration_id)
        for registration_id in confirmed_ids
        if registration_id not in existing_ids
    ]
    already_marked = [
        str(registration_id)
        for registration_id in confirmed_ids
        if registration_id in existing_ids
    ]
    skipped = []
    for registration_id in registration_ids:
        registration = registrations.get(registration_id)
        if registration is None:
            if Registration.objects.filter(pk=registration_id).exists():
                reason = 'Registration does not belong to this event.'
            else:
                reason = 'Registration not found.'
            skipped.append({
                'id': str(registration_id),
                'reason': reason,
            })
        elif registration.status != Registration.Status.CONFIRMED:
            skipped.append({
                'id': str(registration_id),
                'reason': 'Registration is not CONFIRMED.',
            })

    return {
        'marked': marked,
        'already_marked': already_marked,
        'skipped': skipped,
    }


def event_summary(event):
    from decimal import Decimal
    from django.db.models import Count, DecimalField, Q, Sum, Value
    from django.db.models.functions import Coalesce

    days_in_event = (event.end_date - event.start_date).days + 1
    money_field = DecimalField(max_digits=12, decimal_places=2)
    totals = Registration.objects.filter(event=event).aggregate(
        registered=Count('pk', filter=Q(status=Registration.Status.CONFIRMED)),
        cancelled=Count('pk', filter=Q(status=Registration.Status.CANCELLED)),
        revenue=Coalesce(
            Sum('amount_paid', filter=Q(status=Registration.Status.CONFIRMED)),
            Value(Decimal('0.00'), output_field=money_field),
            output_field=money_field,
        ),
    )
    attendees = Registration.objects.filter(
        event=event,
        status=Registration.Status.CONFIRMED,
    ).annotate(days_attended=Count('attendances__date', distinct=True))
    attendance_totals = attendees.aggregate(
        attended_at_least_once=Count('pk', filter=Q(days_attended__gt=0)),
        attended_every_day=Count('pk', filter=Q(days_attended=days_in_event)),
    )
    totals.update(attendance_totals)
    totals['revenue'] = f"{totals['revenue']:.2f}"
    return totals