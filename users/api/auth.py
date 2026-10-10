from datetime import timedelta

from django.utils import timezone
from ninja.security import HttpBearer

from api.common.errors import ApiError
from users.models import ApiTokenSession
from users.tokens import ApiPrincipal, active_member_for_user, hash_token


class MemberBearer(HttpBearer):
    def authenticate(self, request, token):
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
        if not session.last_used_at or now - session.last_used_at > timedelta(minutes=5):
            ApiTokenSession.objects.filter(pk=session.pk).update(last_used_at=now)
        return ApiPrincipal(session.user, member, session)


member_bearer = MemberBearer()


class LogoutBearer(HttpBearer):
    def authenticate(self, request, token):
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
