from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm
from django.db.models import Q
from django.utils import timezone
from ninja import Router

from api.common.errors import ApiError
from api.common.schemas import ErrorSchema, MessageSchema
from audit_logs.services import create_audit_log
from users.api.auth import logout_bearer
from users.api.schemas import (
    PasswordForgotSchema,
    RefreshRequestSchema,
    TokenRequestSchema,
    TokenResponseSchema,
)
from users.models import ApiTokenSession, User
from users.tokens import (
    active_member_for_user,
    issue_token_pair,
    rotate_refresh_token,
    token_response,
)


router = Router(tags=["authentication"])


def user_for_identifier(identifier):
    identifier = identifier.strip()
    phone_candidates = {identifier.replace(" ", "").replace("-", "")}
    if identifier.startswith("0") and len(identifier) > 1:
        phone_candidates.add(f"+255{identifier[1:]}")
    return User.objects.filter(
        Q(username__iexact=identifier) | Q(phone_number__in=phone_candidates)
    ).first()


@router.post(
    "/token",
    auth=None,
    response={200: TokenResponseSchema, 401: ErrorSchema, 403: ErrorSchema},
)
def create_token(request, payload: TokenRequestSchema):
    if payload.device.platform not in dict(ApiTokenSession.PLATFORM_CHOICES):
        raise ApiError(
            "VALIDATION_ERROR",
            "The device platform is invalid.",
            status=422,
            fields={"device.platform": ["Use android or ios."]},
        )
    candidate = user_for_identifier(payload.identifier)
    user = authenticate(
        request,
        username=candidate.username if candidate else payload.identifier,
        password=payload.password,
    )
    if user is None:
        raise ApiError(
            "AUTHENTICATION_FAILED",
            "The identifier or password is incorrect.",
            status=401,
        )

    member = active_member_for_user(user)
    _, access_token, refresh_token = issue_token_pair(user, payload.device)
    create_audit_log(
        user=user,
        church=member.church,
        action="LOGIN",
        description="Member mobile API login.",
        entity_type="ApiTokenSession",
        request=request,
    )
    return token_response(member, access_token, refresh_token)


@router.post(
    "/token/refresh",
    auth=None,
    response={200: TokenResponseSchema, 401: ErrorSchema, 403: ErrorSchema},
)
def refresh_token(request, payload: RefreshRequestSchema):
    return rotate_refresh_token(payload.refresh_token)


@router.post("/logout", auth=logout_bearer, response={204: None})
def logout(request):
    session = request.auth
    ApiTokenSession.objects.filter(
        pk=session.pk,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())
    member = getattr(session.user, "member_profile", None)
    create_audit_log(
        user=session.user,
        church=member.church if member else session.user.church,
        action="LOGOUT",
        description="Member mobile API logout.",
        entity_type="ApiTokenSession",
        entity_id=session.pk,
        request=request,
    )
    return 204, None


@router.post(
    "/password/forgot",
    auth=None,
    response={202: MessageSchema},
)
def forgot_password(request, payload: PasswordForgotSchema):
    form = PasswordResetForm({"email": payload.email.strip()})
    if form.is_valid():
        form.save(
            request=request,
            use_https=request.is_secure(),
            email_template_name="users/password_reset_email.txt",
            subject_template_name="users/password_reset_subject.txt",
        )
    return 202, {
        "message": "If the account exists, password reset instructions have been sent."
    }
