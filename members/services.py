from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from users.models import User

from .models import Member


def validate_church_groups(church, church_groups):
    invalid_groups = [
        group.name for group in church_groups if group.church_id != church.id
    ]
    if invalid_groups:
        raise ValidationError(
            {"church_groups": "All church groups must belong to the selected church."}
        )


@transaction.atomic
def create_member(data):
    church_groups = list(data.get("church_groups") or [])
    validate_church_groups(data["church"], church_groups)
    is_approved = data["approval_status"] == "APPROVED"
    user = User(
        username=data["username"],
        full_name=data["full_name"],
        phone_number=data["phone_number"],
        email=data.get("email", ""),
        church=data["church"],
        role="MEMBER",
        is_active=is_approved,
    )
    user.set_password(data["password"])
    user.full_clean()
    user.save()

    member = Member(
        user=user,
        church=data["church"],
        jumuiya=data.get("jumuiya"),
        bahasha_number=data["bahasha_number"],
        gender=data.get("gender") or None,
        marital_status=data.get("marital_status") or None,
        demographics=data.get("demographics") or "",
        approval_status=data["approval_status"],
        approved_at=timezone.now() if is_approved else None,
        is_active=is_approved,
    )
    member.full_clean()
    member.save()
    member.church_groups.set(church_groups)
    return member


@transaction.atomic
def update_member(member, data):
    church_groups = list(data.get("church_groups") or [])
    validate_church_groups(data["church"], church_groups)
    user = member.user
    user.username = data["username"]
    user.full_name = data["full_name"]
    user.phone_number = data["phone_number"]
    user.email = data.get("email", "")
    user.church = data["church"]
    is_approved = data["approval_status"] == "APPROVED"
    user.is_active = data["is_active"] and is_approved

    member.church = data["church"]
    member.jumuiya = data.get("jumuiya")
    member.bahasha_number = data["bahasha_number"]
    member.gender = data.get("gender") or None
    member.marital_status = data.get("marital_status") or None
    member.demographics = data.get("demographics") or ""
    member.approval_status = data["approval_status"]
    member.is_active = data["is_active"] and is_approved

    if member.approval_status == "APPROVED":
        member.approved_at = member.approved_at or timezone.now()
    else:
        member.approved_at = None

    if member.approval_status == "REJECTED":
        member.is_active = False
        user.is_active = False

    user.full_clean()
    member.full_clean()
    user.save()
    member.save()
    member.church_groups.set(church_groups)
    return member


@transaction.atomic
def approve_member(member):
    member.approval_status = "APPROVED"
    member.approved_at = timezone.now()
    member.is_active = True
    member.user.is_active = True
    member.user.save(update_fields=["is_active", "updated_at"])
    member.save(
        update_fields=["approval_status", "approved_at", "is_active", "updated_at"]
    )
    return member


@transaction.atomic
def reject_member(member):
    member.approval_status = "REJECTED"
    member.approved_at = None
    member.is_active = False
    member.user.is_active = False
    member.user.save(update_fields=["is_active", "updated_at"])
    member.save(
        update_fields=["approval_status", "approved_at", "is_active", "updated_at"]
    )
    return member
