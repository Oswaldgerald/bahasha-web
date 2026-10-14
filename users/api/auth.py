"""Bearer authentication for member-scoped Django Ninja endpoints."""

from datetime import timedelta

from django.utils import timezone
from ninja.security import HttpBearer

from api.common.errors import ApiError
from users.models import ApiTokenSession
from users.tokens import ApiPrincipal, active_member_for_user, hash_token


class MemberBearer(HttpBearer):
    """Resolve a hashed access token to an active, approved member principal."""

    def authenticate(self, request, token):
        """Validate an access token and return its active member principal."""

        now = timezone.now()
        try:
            session = (
                ApiTokenSession.objects.select_related(
                    "user__church",
                    "user__member_profile__church",
                )
                .get(access_token_hash=hash_token(token))
            )
        except ApiTokenSession.DoesNotExist as error:
            raise ApiError(
                "TOKEN_INVALID",
                "The access token is invalid.",
                status=401,
            ) from error

        if session.revoked_at:
            raise ApiError(
                "TOKEN_REVOKED",
                "The access token has been revoked.",
                status=401,
            )
        if session.access_expires_at <= now:
            raise ApiError(
                "TOKEN_EXPIRED",
                "The access token has expired.",
                status=401,
            )

        member = active_member_for_user(session.user)
        # Coalesce activity writes so normal API traffic does not update the token
        # row on every request.
        if not session.last_used_at or now - session.last_used_at > timedelta(minutes=5):
            ApiTokenSession.objects.filter(pk=session.pk).update(last_used_at=now)
        return ApiPrincipal(session.user, member, session)


member_bearer = MemberBearer()


class LogoutBearer(HttpBearer):
    """Resolve revoked sessions too, allowing logout to remain idempotent."""

    def authenticate(self, request, token):
        """Resolve any known session so repeated logout requests can succeed."""

        try:
            return ApiTokenSession.objects.select_related("user__church").get(
                access_token_hash=hash_token(token)
            )
        except ApiTokenSession.DoesNotExist as error:
            raise ApiError(
                "TOKEN_INVALID",
                "The access token is invalid.",
                status=401,
            ) from error


logout_bearer = LogoutBearer()
