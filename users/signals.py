from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from churches.models import Church
from members.models import Member
from users.models import ApiTokenSession, User


def revoke_user_sessions(user_id):
    ApiTokenSession.objects.filter(
        user_id=user_id,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())


@receiver(pre_save, sender=User)
def remember_user_security_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_api_security_state = None
        return
    instance._previous_api_security_state = sender.objects.filter(pk=instance.pk).values(
        "password",
        "is_active",
        "role",
    ).first()


@receiver(post_save, sender=User)
def revoke_sessions_after_user_security_change(sender, instance, created, **kwargs):
    previous = getattr(instance, "_previous_api_security_state", None)
    if created or not previous:
        return
    if (
        previous["password"] != instance.password
        or (previous["is_active"] and not instance.is_active)
        or previous["role"] != instance.role
    ):
        revoke_user_sessions(instance.pk)


@receiver(post_save, sender=Member)
def revoke_sessions_for_ineligible_member(sender, instance, **kwargs):
    if not instance.is_active or instance.approval_status != "APPROVED":
        revoke_user_sessions(instance.user_id)


@receiver(post_save, sender=Church)
def revoke_sessions_for_inactive_church(sender, instance, **kwargs):
    if not instance.is_active:
        ApiTokenSession.objects.filter(
            user__church=instance,
            revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
