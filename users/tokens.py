import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from api.common.errors import ApiError
from members.models import Member
from users.models import ApiTokenSession, User


ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
REFRESH_TOKEN_LIFETIME = timedelta(days=30)


@dataclass(frozen=True)
class ApiPrincipal:
    user: User
    member: Member
    session: ApiTokenSession


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def random_token():
    return secrets.token_urlsafe(48)


def active_member_for_user(user):
    if not user.is_active:
        raise ApiError(
            "ACCOUNT_INACTIVE",
            "This account is inactive.",
            status=403,
        )
    if user.role != "MEMBER" or user.is_superuser:
        raise ApiError(
            "FORBIDDEN",
            "This account cannot use the member application.",
            status=403,
        )
    try:
        member = user.member_profile
    except Member.DoesNotExist as error:
        raise ApiError(
            "FORBIDDEN",
            "A member profile is required.",
            status=403,
        ) from error
    if not member.is_active or member.approval_status != "APPROVED":
        raise ApiError(
            "MEMBER_NOT_APPROVED",
            "Your membership is awaiting approval.",
            status=403,
        )
    if not member.church.is_active:
        raise ApiError(
            "CHURCH_INACTIVE",
            "Your church is currently inactive.",
            status=403,
        )
    return member


def issue_token_pair(user, device, *, family_id=None):
    now = timezone.now()
    access_token = random_token()
    refresh_token = random_token()
    session_values = {
        "user": user,
        "access_token_hash": hash_token(access_token),
        "refresh_token_hash": hash_token(refresh_token),
        "installation_id": device.installation_id,
        "platform": device.platform,
        "app_version": device.app_version,
        "device_name": device.device_name,
        "access_expires_at": now + ACCESS_TOKEN_LIFETIME,
        "refresh_expires_at": now + REFRESH_TOKEN_LIFETIME,
    }
    if family_id is not None:
        session_values["family_id"] = family_id
    session = ApiTokenSession.objects.create(
        **session_values,
    )
    return session, access_token, refresh_token


def token_response(member, access_token, refresh_token):
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": int(ACCESS_TOKEN_LIFETIME.total_seconds()),
        "member": {
            "id": member.public_id,
            "full_name": member.user.full_name,
            "approval_status": member.approval_status.lower(),
        },
    }


def rotate_refresh_token(raw_refresh_token):
    now = timezone.now()
    deferred_error = None
    response = None
    with transaction.atomic():
        try:
            session = (
                ApiTokenSession.objects.select_for_update()
                .get(refresh_token_hash=hash_token(raw_refresh_token))
            )
        except ApiTokenSession.DoesNotExist as error:
            raise ApiError(
                "TOKEN_INVALID",
                "The refresh token is invalid.",
                status=401,
            ) from error

        if session.revoked_at:
            ApiTokenSession.objects.filter(
                family_id=session.family_id,
                revoked_at__isnull=True,
            ).update(revoked_at=now)
            deferred_error = ApiError(
                "TOKEN_REVOKED",
                "The refresh token has already been used or revoked.",
                status=401,
            )
        elif session.refresh_expires_at <= now:
            session.revoked_at = now
            session.save(update_fields=["revoked_at", "updated_at"])
            deferred_error = ApiError(
                "TOKEN_EXPIRED",
                "The refresh token has expired.",
                status=401,
            )
        else:
            member = active_member_for_user(session.user)
            session.revoked_at = now
            session.save(update_fields=["revoked_at", "updated_at"])
            device = type(
                "Device",
                (),
                {
                    "installation_id": session.installation_id,
                    "platform": session.platform,
                    "app_version": session.app_version,
                    "device_name": session.device_name,
                },
            )
            _, access_token, refresh_token = issue_token_pair(
                session.user,
                device,
                family_id=session.family_id,
            )
            response = token_response(member, access_token, refresh_token)

    if deferred_error:
        raise deferred_error
    return response
