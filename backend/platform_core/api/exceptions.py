"""
Enterprise API Exceptions

Every REST API in One UCH should raise
one of these exceptions.

Never raise generic Exception from API code.
"""

from rest_framework.exceptions import APIException
from rest_framework import status


class EnterpriseAPIException(APIException):

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    default_detail = "Platform Error."

    default_code = "platform_error"


class ValidationException(EnterpriseAPIException):

    status_code = status.HTTP_400_BAD_REQUEST

    default_detail = "Validation failed."

    default_code = "validation_error"


class ResourceNotFoundException(EnterpriseAPIException):

    status_code = status.HTTP_404_NOT_FOUND

    default_detail = "Resource not found."

    default_code = "not_found"


class PermissionDeniedException(EnterpriseAPIException):

    status_code = status.HTTP_403_FORBIDDEN

    default_detail = "Permission denied."

    default_code = "permission_denied"


class AuthenticationException(EnterpriseAPIException):

    status_code = status.HTTP_401_UNAUTHORIZED

    default_detail = "Authentication required."

    default_code = "authentication_required"


class ConflictException(EnterpriseAPIException):

    status_code = status.HTTP_409_CONFLICT

    default_detail = "Conflict detected."

    default_code = "conflict"