import datetime
from rest_framework.exceptions import ValidationError


def filter_events(queryset, params):
    """
    Filter events queryset based on query parameters.
    Raises rest_framework ValidationError (HTTP 400) on invalid inputs.
    """
    is_published_param = params.get('is_published')
    if is_published_param is not None:
        normalized = is_published_param.strip().casefold()
        if normalized not in {'true', 'false'}:
            raise ValidationError({
                'is_published': "Invalid value. Use 'true' or 'false'."
            })
        queryset = queryset.filter(is_published=(normalized == 'true'))

    start_date_after_param = params.get('start_date_after')
    if start_date_after_param is not None:
        try:
            parsed_date = datetime.date.fromisoformat(
                start_date_after_param.strip()
            )
        except (ValueError, TypeError):
            raise ValidationError({
                'start_date_after': "Invalid date format. Use YYYY-MM-DD."
            })
        queryset = queryset.filter(start_date__gte=parsed_date)

    return queryset
