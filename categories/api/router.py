from uuid import UUID

from django.db.models import Sum
from django.utils import timezone
from ninja import Router

from api.common.errors import ApiError
from api.common.pagination import paginate
from api.common.schemas import ErrorSchema
from categories.api.schemas import (
    CategoryCardSchema,
    CategoryListSchema,
    WeekListSchema,
)
from categories.api.services import category_cards, money
from categories.models import ContributionCategory
from contribution_weeks.models import ContributionWeek
from contributions.models import Contribution
from financial_years.models import FinancialYear
from users.api.auth import member_bearer


router = Router(auth=member_bearer, tags=["contribution categories"])


def selected_year(member, financial_year_id=None):
    years = FinancialYear.objects.filter(church=member.church)
    if financial_year_id:
        try:
            return years.get(public_id=financial_year_id)
        except FinancialYear.DoesNotExist as error:
            raise ApiError(
                "NOT_FOUND",
                "The financial year was not found.",
                status=404,
            ) from error
    return years.filter(is_active=True).order_by("-year").first()


def selected_category(member, category_id):
    try:
        return ContributionCategory.objects.get(
            public_id=category_id,
            church=member.church,
            is_active=True,
            is_mobile_visible=True,
        )
    except ContributionCategory.DoesNotExist as error:
        raise ApiError(
            "NOT_FOUND",
            "The contribution category was not found.",
            status=404,
        ) from error


@router.get("/contribution-categories", response=CategoryListSchema)
def list_categories(request, financial_year_id: UUID | None = None):
    year = selected_year(request.auth.member, financial_year_id)
    return {"items": category_cards(request.auth.member, year)}


@router.get(
    "/contribution-categories/{category_id}",
    response={200: CategoryCardSchema, 404: ErrorSchema},
)
def category_detail(request, category_id: UUID, financial_year_id: UUID | None = None):
    category = selected_category(request.auth.member, category_id)
    year = selected_year(request.auth.member, financial_year_id)
    cards = category_cards(request.auth.member, year)
    return next(card for card in cards if card["id"] == category.public_id)


@router.get(
    "/contribution-categories/{category_id}/weeks",
    response={200: WeekListSchema, 404: ErrorSchema},
)
def category_weeks(
    request,
    category_id: UUID,
    financial_year_id: UUID | None = None,
    state: str | None = None,
    cursor: str | None = None,
    page_size: int = 20,
):
    member = request.auth.member
    category = selected_category(member, category_id)
    year = selected_year(member, financial_year_id)
    if category.frequency != "WEEKLY" or year is None:
        return {"items": [], "page": {"next_cursor": None, "has_more": False}}

    valid_states = {"paid", "missing", "upcoming", "unavailable"}
    if state and state not in valid_states:
        raise ApiError(
            "VALIDATION_ERROR",
            "The week state is invalid.",
            status=422,
            fields={"state": ["Use paid, missing, upcoming, or unavailable."]},
        )

    weeks = list(
        ContributionWeek.objects.filter(
            church=member.church,
            financial_year=year,
        )
    )
    totals = {
        row["contribution_week_id"]: row["total"]
        for row in Contribution.objects.filter(
            member=member,
            church=member.church,
            financial_year=year,
            category=category,
            status="POSTED",
        )
        .values("contribution_week_id")
        .annotate(total=Sum("amount"))
    }
    today = timezone.localdate()
    weeks.sort(
        key=lambda week: (
            not week.is_active,
            week.sunday_date > today,
            abs((week.sunday_date - today).days),
        )
    )
    results = []
    for week in weeks:
        contributed = totals.get(week.pk)
        if contributed:
            week_state = "paid"
            payment_eligible = False
        elif week.sunday_date > today:
            week_state = "upcoming"
            payment_eligible = False
        elif category.allows_member_payment and category.allows_catch_up:
            week_state = "missing"
            payment_eligible = True
        else:
            week_state = "unavailable"
            payment_eligible = False
        if state and state != week_state:
            continue
        results.append(
            {
                "id": week.public_id,
                "week_number": week.week_number,
                "sunday_date": week.sunday_date.isoformat(),
                "state": week_state,
                "payment_eligible": payment_eligible,
                "contributed": money(contributed),
                "expected": None,
                "remaining": None,
            }
        )
    items, page = paginate(results, cursor=cursor, page_size=page_size)
    return {"items": items, "page": page}
