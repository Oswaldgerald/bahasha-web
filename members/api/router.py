from django import forms
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from ninja import File, Router, UploadedFile

from api.common.errors import ApiError
from audit_logs.services import create_audit_log
from categories.api.services import category_cards
from contribution_weeks.models import ContributionWeek
from financial_years.models import FinancialYear
from members.api.schemas import BootstrapSchema, MemberSchema, MemberUpdateSchema
from members.api.serializers import member_payload
from notifications.models import Notification, NotificationReceipt
from users.api.auth import member_bearer
from users.profile_pictures import validate_profile_picture
from users.profile_pictures import profile_picture_response


router = Router(auth=member_bearer, tags=["member"])


def hydrated_member(member):
    return (
        type(member)
        .objects.select_related("user", "church", "jumuiya")
        .prefetch_related("church_groups")
        .get(pk=member.pk)
    )


@router.get("/me", response=MemberSchema)
def get_me(request):
    return member_payload(hydrated_member(request.auth.member))


@router.patch("/me", response=MemberSchema)
@transaction.atomic
def update_me(request, payload: MemberUpdateSchema):
    user = request.auth.user
    values = payload.model_dump(exclude_unset=True)
    if "full_name" in values:
        full_name = (values["full_name"] or "").strip()
        if len(full_name) < 2:
            raise ApiError(
                "VALIDATION_ERROR",
                "The profile could not be updated.",
                status=422,
                fields={"full_name": ["Enter at least two characters."]},
            )
        user.full_name = full_name
    if "email" in values:
        email = (values["email"] or "").strip().lower()
        if email:
            try:
                forms.EmailField().clean(email)
            except forms.ValidationError as error:
                raise ApiError(
                    "VALIDATION_ERROR",
                    "The profile could not be updated.",
                    status=422,
                    fields={"email": list(error.messages)},
                ) from error
        user.email = email
    user.save(update_fields=["full_name", "email", "updated_at"])
    create_audit_log(
        user=user,
        church=request.auth.member.church,
        action="PROFILE_UPDATED",
        description="Member updated their mobile profile.",
        entity_type="User",
        entity_id=user.pk,
        request=request,
    )
    return member_payload(hydrated_member(request.auth.member))


@router.get("/me/photo", response=None)
def get_photo(request):
    try:
        return profile_picture_response(request.auth.user)
    except Http404 as error:
        raise ApiError(
            "NOT_FOUND",
            "The profile photo was not found.",
            status=404,
        ) from error


@router.post("/me/photo", response=MemberSchema)
def update_photo(request, photo: File[UploadedFile]):
    try:
        cleaned_photo = forms.ImageField().clean(photo)
        validate_profile_picture(cleaned_photo)
    except forms.ValidationError as error:
        raise ApiError(
            "VALIDATION_ERROR",
            "The profile photo is invalid.",
            status=422,
            fields={"photo": list(error.messages)},
        ) from error
    user = request.auth.user
    if user.profile_picture:
        user.profile_picture.delete(save=False)
    user.profile_picture = cleaned_photo
    user.save(update_fields=["profile_picture", "updated_at"])
    create_audit_log(
        user=user,
        church=request.auth.member.church,
        action="PROFILE_UPDATED",
        description="Member updated their mobile profile photo.",
        entity_type="User",
        entity_id=user.pk,
        request=request,
    )
    return member_payload(hydrated_member(request.auth.member))


@router.delete("/me/photo", response={204: None})
def delete_photo(request):
    user = request.auth.user
    if user.profile_picture:
        user.profile_picture.delete(save=False)
        user.profile_picture = ""
        user.save(update_fields=["profile_picture", "updated_at"])
        create_audit_log(
            user=user,
            church=request.auth.member.church,
            action="PROFILE_UPDATED",
            description="Member removed their mobile profile photo.",
            entity_type="User",
            entity_id=user.pk,
            request=request,
        )
    return 204, None


@router.get("/bootstrap", response=BootstrapSchema)
def bootstrap(request):
    member = hydrated_member(request.auth.member)
    active_year = (
        FinancialYear.objects.filter(church=member.church, is_active=True)
        .order_by("-year")
        .first()
    )
    active_week = None
    if active_year:
        active_week = (
            ContributionWeek.objects.filter(
                church=member.church,
                financial_year=active_year,
                is_active=True,
            )
            .order_by("-sunday_date")
            .first()
        )
    visible_notifications = Notification.objects.filter(
        church=member.church,
        status="SENT",
    ).filter(
        Q(target_role__isnull=True)
        | Q(target_role="")
        | Q(target_role=member.user.role)
    )
    read_ids = NotificationReceipt.objects.filter(
        user=member.user,
        read_at__isnull=False,
    ).values_list("notification_id", flat=True)
    unread_count = visible_notifications.exclude(pk__in=read_ids).count()
    return {
        "member": member_payload(member),
        "active_period": {
            "financial_year": (
                {"id": active_year.public_id, "year": active_year.year}
                if active_year
                else None
            ),
            "week": (
                {
                    "id": active_week.public_id,
                    "number": active_week.week_number,
                    "sunday_date": active_week.sunday_date.isoformat(),
                    "is_closed": active_week.is_closed,
                }
                if active_week
                else None
            ),
        },
        "categories": category_cards(member, active_year),
        "unread_notifications_count": unread_count,
        "capabilities": {
            "payments_enabled": False,
            "profile_photo_upload": True,
            "push_notifications": False,
        },
    }
