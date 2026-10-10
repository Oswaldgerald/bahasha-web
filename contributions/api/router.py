from datetime import date
from uuid import UUID

from ninja import Router

from annual_targets.models import MemberAnnualTarget
from api.common.errors import ApiError
from api.common.pagination import paginate
from api.common.schemas import ErrorSchema
from categories.api.services import money
from contributions.api.schemas import (
    ContributionDetailSchema,
    ContributionListSchema,
    TargetListSchema,
    YearListSchema,
)
from contributions.models import Contribution
from financial_years.models import FinancialYear
from users.api.auth import member_bearer


router = Router(auth=member_bearer, tags=["contributions"])


def year_payload(year):
    return {
        "id": year.public_id,
        "year": year.year,
        "start_date": year.start_date.isoformat(),
        "end_date": year.end_date.isoformat(),
        "is_active": year.is_active,
    }


def category_reference(category):
    return {
        "id": category.public_id,
        "key": category.key,
        "name": category.name,
    }


def contribution_payload(contribution):
    return {
        "id": contribution.public_id,
        "reference": contribution.reference_number,
        "category": category_reference(contribution.category),
        "week": {
            "id": contribution.contribution_week.public_id,
            "number": contribution.contribution_week.week_number,
            "sunday_date": contribution.contribution_week.sunday_date.isoformat(),
        },
        "amount": money(contribution.amount),
        "source": contribution.source.lower(),
        "status": contribution.status.lower(),
        "contribution_date": contribution.contribution_date.isoformat(),
        "posted_at": contribution.posted_at.isoformat().replace("+00:00", "Z"),
    }


@router.get("/financial-years", response=YearListSchema)
def financial_years(request):
    years = FinancialYear.objects.filter(church=request.auth.member.church).order_by(
        "-year"
    )
    return {"items": [year_payload(year) for year in years]}


@router.get("/targets", response=TargetListSchema)
def targets(
    request,
    financial_year_id: UUID | None = None,
    category_id: UUID | None = None,
    cursor: str | None = None,
    page_size: int = 20,
):
    queryset = MemberAnnualTarget.objects.filter(
        member=request.auth.member,
        church=request.auth.member.church,
    ).select_related("financial_year", "category")
    if financial_year_id:
        queryset = queryset.filter(financial_year__public_id=financial_year_id)
    if category_id:
        queryset = queryset.filter(category__public_id=category_id)
    target_items, page = paginate(queryset, cursor=cursor, page_size=page_size)
    items = [
        {
            "id": target.public_id,
            "financial_year": {
                "id": target.financial_year.public_id,
                "year": target.financial_year.year,
            },
            "category": category_reference(target.category),
            "target": money(target.target_amount),
            "contributed": money(target.contributed_amount),
            "remaining": money(target.remaining_amount),
            "completion_percentage": f"{target.completion_percentage:.2f}",
        }
        for target in target_items
    ]
    return {"items": items, "page": page}


@router.get("/contributions", response=ContributionListSchema)
def contributions(
    request,
    category_id: UUID | None = None,
    financial_year_id: UUID | None = None,
    week_id: UUID | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    cursor: str | None = None,
    page_size: int = 20,
):
    queryset = Contribution.objects.filter(
        member=request.auth.member,
        church=request.auth.member.church,
    ).select_related("category", "contribution_week", "financial_year")
    if category_id:
        queryset = queryset.filter(category__public_id=category_id)
    if financial_year_id:
        queryset = queryset.filter(financial_year__public_id=financial_year_id)
    if week_id:
        queryset = queryset.filter(contribution_week__public_id=week_id)
    if status:
        normalized_status = status.upper()
        if normalized_status not in dict(Contribution.STATUS_CHOICES):
            raise ApiError(
                "VALIDATION_ERROR",
                "The contribution status is invalid.",
                status=422,
                fields={"status": ["Use posted, pending, or reversed."]},
            )
        queryset = queryset.filter(status=normalized_status)
    if date_from:
        queryset = queryset.filter(contribution_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(contribution_date__lte=date_to)
    contribution_items, page = paginate(
        queryset.order_by("-contribution_date", "-created_at"),
        cursor=cursor,
        page_size=page_size,
    )
    return {
        "items": [contribution_payload(item) for item in contribution_items],
        "page": page,
    }


@router.get(
    "/contributions/{contribution_id}",
    response={200: ContributionDetailSchema, 404: ErrorSchema},
)
def contribution_detail(request, contribution_id: UUID):
    try:
        contribution = Contribution.objects.select_related(
            "category",
            "contribution_week",
            "financial_year",
            "church",
        ).get(
            public_id=contribution_id,
            member=request.auth.member,
            church=request.auth.member.church,
        )
    except Contribution.DoesNotExist as error:
        raise ApiError(
            "NOT_FOUND",
            "The contribution was not found.",
            status=404,
        ) from error
    payload = contribution_payload(contribution)
    payload.update(
        {
            "financial_year": year_payload(contribution.financial_year),
            "remarks": contribution.remarks or "",
            "church": {
                "id": contribution.church.public_id,
                "code": contribution.church.church_code,
                "name": contribution.church.church_name,
            },
        }
    )
    return payload
