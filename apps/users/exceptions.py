from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, AuthenticationFailed, NotAuthenticated
from rest_framework.permissions import IsAuthenticated


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Convert 403 to 401 for authentication-related issues
        # NotAuthenticated is raised by authentication classes
        # PermissionDenied with certain messages is raised by permission classes
        if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            response.status_code = 401
        elif (response.status_code == 403 and
                isinstance(exc, PermissionDenied)):
            # Check if this is related to authentication
            detail = str(exc.detail).lower()
            if 'auth' in detail or 'credential' in detail or 'login' in detail:
                response.status_code = 401

        custom_response_data = {
            'code': getattr(exc, 'custom_code', response.status_code * 100),
            'message': str(exc.detail if hasattr(exc, 'detail') else exc),
            'errors': response.data if hasattr(response, 'data') else None
        }
        response.data = custom_response_data

    return response


class CustomAPIException(Exception):
    def __init__(self, code, message, errors=None):
        self.code = code
        self.message = message
        self.errors = errors
        super().__init__(message)
