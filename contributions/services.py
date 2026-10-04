from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from annual_targets.models import MemberAnnualTarget

from .models import Contribution


def contribution_target_key(contribution):
    return (
        contribution.member_id,
        contribution.church_id,
        contribution.financial_year_id,
        contribution.category_id,
    )


def recalculate_target(key):
    member_id, church_id, financial_year_id, category_id = key
    target = MemberAnnualTarget.objects.select_for_update().filter(
        member_id=member_id,
        church_id=church_id,
        financial_year_id=financial_year_id,
        category_id=category_id,
    ).first()

    if not target:
        return

    total = Contribution.objects.filter(
        member_id=member_id,
        church_id=church_id,
        financial_year_id=financial_year_id,
        category_id=category_id,
        status="POSTED",
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    target.contributed_amount = total
    target.save()


@transaction.atomic
def save_contributions(contributions, previous_target_keys=()):
    affected_targets = set(previous_target_keys)
    saved_contributions = []

    for contribution in contributions:
        if contribution.member_id:
            contribution.bahasha_number = contribution.member.bahasha_number

        contribution.full_clean()
        contribution.save()
        affected_targets.add(contribution_target_key(contribution))
        saved_contributions.append(contribution)

    for key in affected_targets:
        recalculate_target(key)

    return saved_contributions


def save_contribution(contribution, previous_target_key=None):
    previous_keys = [previous_target_key] if previous_target_key else []
    return save_contributions([contribution], previous_keys)[0]
