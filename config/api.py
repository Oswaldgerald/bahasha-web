from django.conf import settings
from ninja import NinjaAPI
from ninja.errors import AuthenticationError, ValidationError as NinjaValidationError

from api.common.errors import ApiError, error_response
from api.v1.router import router as v1_router


api = NinjaAPI(
    title="Bahasha Member API",
    version="1.0.0",
    urls_namespace="bahasha_api_v1",
    docs_url="/docs" if settings.DEBUG else None,
    openapi_url="/openapi.json",
)


@api.exception_handler(ApiError)
def handle_api_error(request, exc):
    return error_response(
        request,
        exc.code,
        exc.message,
        status=exc.status,
        fields=exc.fields,
    )


@api.exception_handler(AuthenticationError)
def handle_authentication_error(request, exc):
    return error_response(
        request,
        "TOKEN_INVALID",
        "Authentication credentials were not provided or are invalid.",
        status=401,
    )


@api.exception_handler(NinjaValidationError)
def handle_validation_error(request, exc):
    raw_errors = exc.errors
    if callable(raw_errors):
        raw_errors = raw_errors()
    fields = {}
    for error in raw_errors:
        location = error.get("loc", ())
        field = str(location[-1]) if location else "request"
        fields.setdefault(field, []).append(error.get("msg", "Invalid value."))
    return error_response(
        request,
        "VALIDATION_ERROR",
        "One or more request fields are invalid.",
        status=422,
        fields=fields,
    )


api.add_router("", v1_router)
