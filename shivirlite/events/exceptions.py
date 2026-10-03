from rest_framework.exceptions import APIException, ValidationError


class Conflict(APIException):
    status_code = 409
    default_detail = 'This registration conflicts with an existing registration.'
    default_code = 'conflict'


DuplicateRegistrationError = Conflict


def bad_request(message):
    return ValidationError({'detail': message})

