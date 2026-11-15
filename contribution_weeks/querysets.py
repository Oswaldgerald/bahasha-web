from datetime import timedelta

from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone


def current_week_first(queryset, *, today=None):
    """Order active/current contribution weeks before the newest remaining weeks."""

    today = today or timezone.localdate()
    current_sunday = today - timedelta(days=(today.weekday() + 1) % 7)
    return queryset.annotate(
        week_order_priority=Case(
            When(is_active=True, then=Value(0)),
            When(sunday_date=current_sunday, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    ).order_by(
        "week_order_priority",
        "-sunday_date",
        "-week_number",
        "church__church_name",
        "-pk",
    )
