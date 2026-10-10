from django.http import JsonResponse


class ApiError(Exception):
    def __init__(self, code, message, *, status=400, fields=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.fields = fields or {}


def error_payload(request, code, message, fields=None):
    return {
        "error": {
            "code": code,
            "message": message,
            "fields": fields or {},
            "request_id": getattr(request, "request_id", ""),
        }
    }


def error_response(request, code, message, *, status, fields=None):
    return JsonResponse(
        error_payload(request, code, message, fields),
        status=status,
    )
