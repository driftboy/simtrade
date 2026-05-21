from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
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
