from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from categories.models import ContributionCategory
from contribution_weeks.models import ContributionWeek
from contributions.models import Contribution


def money(value):
    value = value if value is not None else Decimal("0.00")
    return {"amount": f"{value:.2f}", "currency": "TZS"}


def optional_money(value):
    return money(value) if value is not None else None


def category_cards(member, financial_year):
    categories = list(
        ContributionCategory.objects.filter(
            church=member.church,
            is_active=True,
            is_mobile_visible=True,
        ).order_by("display_order", "name")
    )
    if not categories:
        return []

    contribution_filter = {
        "member": member,
        "church": member.church,
        "status": "POSTED",
    }
    if financial_year:
        contribution_filter["financial_year"] = financial_year
    totals = {
        item["category_id"]: item["total"]
        for item in Contribution.objects.filter(**contribution_filter)
        .values("category_id")
        .annotate(total=Sum("amount"))
    }

    eligible_weeks = []
    paid_pairs = set()
    if financial_year:
        eligible_weeks = list(
            ContributionWeek.objects.filter(
                church=member.church,
                financial_year=financial_year,
                sunday_date__lte=timezone.localdate(),
            ).values_list("id", flat=True)
        )
        paid_pairs = set(
            Contribution.objects.filter(
                member=member,
                church=member.church,
                financial_year=financial_year,
                status="POSTED",
                contribution_week_id__in=eligible_weeks,
            ).values_list("category_id", "contribution_week_id")
        )

    cards = []
    for category in categories:
        missing_count = 0
        if (
            category.frequency == "WEEKLY"
            and category.allows_member_payment
            and category.allows_catch_up
        ):
            missing_count = sum(
                (category.pk, week_id) not in paid_pairs
                for week_id in eligible_weeks
            )
        cards.append(
            {
                "id": category.public_id,
                "key": category.key,
                "labels": {
                    "default": category.name,
                    "sw": category.name_sw or category.name,
                },
                "description": category.description or "",
                "icon": category.icon_key,
                "color": category.theme_color,
                "frequency": category.frequency.lower(),
                "display_order": category.display_order,
                "payments_enabled": category.allows_member_payment,
                "allows_catch_up": category.allows_catch_up,
                "amount_guidance": {
                    "suggested": optional_money(category.suggested_amount),
                    "minimum": optional_money(category.minimum_amount),
                    "maximum": optional_money(category.maximum_amount),
                },
                "missing_weeks_count": missing_count,
                "total_contributed": money(totals.get(category.pk)),
            }
        )
    return cards
