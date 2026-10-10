from uuid import UUID

from django.db.models import Q
from django.utils import timezone
from ninja import Router

from api.common.errors import ApiError
from api.common.pagination import paginate
from api.common.schemas import ErrorSchema
from audit_logs.services import create_audit_log
from notifications.api.schemas import (
    DeviceRequestSchema,
    DeviceSchema,
    NotificationListSchema,
)
from notifications.models import MobileDevice, Notification, NotificationReceipt
from users.api.auth import member_bearer


router = Router(auth=member_bearer, tags=["notifications"])


def visible_notifications(principal):
    return Notification.objects.filter(
        church=principal.member.church,
        status="SENT",
    ).filter(
        Q(target_role__isnull=True)
        | Q(target_role="")
        | Q(target_role=principal.user.role)
    )


@router.get("/notifications", response=NotificationListSchema)
def notification_list(
    request,
    unread_only: bool = False,
    cursor: str | None = None,
    page_size: int = 20,
):
    queryset = visible_notifications(request.auth).order_by("-sent_at", "-created_at")
    read_receipts = NotificationReceipt.objects.filter(
        user=request.auth.user,
        read_at__isnull=False,
    )
    if unread_only:
        queryset = queryset.exclude(
            pk__in=read_receipts.values_list("notification_id", flat=True)
        )
    notification_items, page = paginate(
        queryset,
        cursor=cursor,
        page_size=page_size,
    )
    receipt_by_notification = {
        receipt.notification_id: receipt
        for receipt in NotificationReceipt.objects.filter(
            user=request.auth.user,
            notification_id__in=[item.pk for item in notification_items],
        )
    }
    items = []
    for notification in notification_items:
        receipt = receipt_by_notification.get(notification.pk)
        items.append(
            {
                "id": notification.public_id,
                "title": notification.title,
                "message": notification.message,
                "notification_type": notification.notification_type.lower(),
                "sent_at": notification.sent_at,
                "is_read": bool(receipt and receipt.read_at),
                "read_at": receipt.read_at if receipt else None,
            }
        )
    return {"items": items, "page": page}


@router.post(
    "/notifications/{notification_id}/read",
    response={204: None, 404: ErrorSchema},
)
def mark_notification_read(request, notification_id: UUID):
    try:
        notification = visible_notifications(request.auth).get(
            public_id=notification_id
        )
    except Notification.DoesNotExist as error:
        raise ApiError(
            "NOT_FOUND",
            "The notification was not found.",
            status=404,
        ) from error
    receipt, _ = NotificationReceipt.objects.get_or_create(
        notification=notification,
        user=request.auth.user,
    )
    if not receipt.read_at:
        receipt.read_at = timezone.now()
        receipt.save(update_fields=["read_at"])
    return 204, None


def device_payload(device):
    return {
        "id": device.public_id,
        "installation_id": device.installation_id,
        "platform": device.platform,
        "app_version": device.app_version,
        "is_active": device.is_active,
    }


@router.post(
    "/devices",
    response={200: DeviceSchema, 201: DeviceSchema},
)
def register_device(request, payload: DeviceRequestSchema):
    if payload.platform not in dict(MobileDevice.PLATFORM_CHOICES):
        raise ApiError(
            "VALIDATION_ERROR",
            "The device platform is invalid.",
            status=422,
            fields={"platform": ["Use android or ios."]},
        )
    push_token = payload.push_token.strip()
    if not push_token:
        raise ApiError(
            "VALIDATION_ERROR",
            "The push token is required.",
            status=422,
            fields={"push_token": ["Enter a push token."]},
        )
    device, created = MobileDevice.objects.update_or_create(
        user=request.auth.user,
        installation_id=payload.installation_id,
        defaults={
            "platform": payload.platform,
            "push_token": push_token,
            "app_version": payload.app_version.strip(),
            "is_active": True,
        },
    )
    create_audit_log(
        user=request.auth.user,
        church=request.auth.member.church,
        action="DEVICE_REGISTERED",
        description="Member registered a mobile notification device.",
        entity_type="MobileDevice",
        entity_id=device.pk,
        request=request,
    )
    return (201 if created else 200), device_payload(device)


@router.delete(
    "/devices/{device_id}",
    response={204: None, 404: ErrorSchema},
)
def unregister_device(request, device_id: UUID):
    try:
        device = MobileDevice.objects.get(
            public_id=device_id,
            user=request.auth.user,
        )
    except MobileDevice.DoesNotExist as error:
        raise ApiError(
            "NOT_FOUND",
            "The mobile device was not found.",
            status=404,
        ) from error
    if device.is_active:
        device.is_active = False
        device.save(update_fields=["is_active", "last_seen_at"])
    return 204, None
