from django.http import JsonResponse


class ApiError(Exception):
    """Structured application error converted to the standard API error shape."""

    def __init__(self, code, message, *, status=400, fields=None):
        """Capture client-safe error details for the Ninja exception handler."""

        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.fields = fields or {}


def error_payload(request, code, message, fields=None):
    """Build a stable error body carrying the request correlation identifier."""

    return {
        "error": {
            "code": code,
            "message": message,
            "fields": fields or {},
            "request_id": getattr(request, "request_id", ""),
        }
    }


def error_response(request, code, message, *, status, fields=None):
    """Return a JSON response using the shared API error contract."""

    return JsonResponse(
        error_payload(request, code, message, fields),
        status=status,
    )
