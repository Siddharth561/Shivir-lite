import phonenumbers


def normalize_phone(raw, default_region='IN'):
    try:
        number = phonenumbers.parse(raw, default_region)
    except phonenumbers.NumberParseException as error:
        raise ValueError('Invalid phone number.') from error

    if not phonenumbers.is_valid_number(number):
        raise ValueError('Invalid phone number.')

    return phonenumbers.format_number(
        number, phonenumbers.PhoneNumberFormat.E164
    )
