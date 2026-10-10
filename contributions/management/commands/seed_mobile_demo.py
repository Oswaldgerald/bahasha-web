from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from annual_targets.models import MemberAnnualTarget
from categories.models import ContributionCategory
from contribution_weeks.models import ContributionWeek
from contributions.models import Contribution
from financial_years.models import FinancialYear
from members.models import Member


CATEGORY_SETTINGS = {
    "ahadi": {
        "suggested": Decimal("5000.00"),
        "minimum": Decimal("1000.00"),
        "maximum": Decimal("100000.00"),
        "target": Decimal("260000.00"),
        "payments": [(0, "5000.00"), (1, "5000.00"), (3, "10000.00"), (5, "5000.00")],
    },
    "jumuiya": {
        "suggested": Decimal("3000.00"),
        "minimum": Decimal("1000.00"),
        "maximum": Decimal("50000.00"),
        "target": Decimal("156000.00"),
        "payments": [(0, "3000.00"), (2, "6000.00"), (4, "3000.00")],
    },
    "jengo": {
        "suggested": Decimal("20000.00"),
        "minimum": Decimal("5000.00"),
        "maximum": Decimal("500000.00"),
        "target": Decimal("300000.00"),
        "payments": [(1, "50000.00"), (6, "25000.00")],
    },
    "uwakili": {
        "suggested": Decimal("10000.00"),
        "minimum": Decimal("2000.00"),
        "maximum": Decimal("200000.00"),
        "target": Decimal("120000.00"),
        "payments": [(2, "10000.00"), (7, "10000.00")],
    },
    "mavuno": {
        "suggested": Decimal("25000.00"),
        "minimum": Decimal("5000.00"),
        "maximum": Decimal("500000.00"),
        "target": Decimal("150000.00"),
        "payments": [(4, "30000.00")],
    },
}


class Command(BaseCommand):
    help = "Create idempotent mobile demo contributions for an approved member."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Username of the approved member")

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["username"].strip()
        try:
            member = Member.objects.select_related("user", "church").get(
                user__username__iexact=username,
                approval_status="APPROVED",
                is_active=True,
                user__is_active=True,
            )
        except Member.DoesNotExist as error:
            raise CommandError(
                f'No active approved member exists for username "{username}".'
            ) from error

        year = (
            FinancialYear.objects.filter(church=member.church, is_active=True)
            .order_by("-year")
            .first()
        )
        if year is None:
            raise CommandError("The member's church has no active financial year.")

        weeks = list(
            ContributionWeek.objects.filter(
                church=member.church,
                financial_year=year,
                sunday_date__lte=timezone.localdate(),
            ).order_by("-sunday_date")[:8]
        )
        if len(weeks) < 8:
            raise CommandError("At least eight elapsed contribution weeks are required.")

        categories = {
            category.key: category
            for category in ContributionCategory.objects.filter(
                church=member.church,
                key__in=CATEGORY_SETTINGS,
            )
        }
        missing = sorted(set(CATEGORY_SETTINGS) - set(categories))
        if missing:
            raise CommandError(f"Missing contribution categories: {', '.join(missing)}")

        created_count = 0
        for key, settings in CATEGORY_SETTINGS.items():
            category = categories[key]
            category.suggested_amount = settings["suggested"]
            category.minimum_amount = settings["minimum"]
            category.maximum_amount = settings["maximum"]
            category.save(
                update_fields=[
                    "suggested_amount",
                    "minimum_amount",
                    "maximum_amount",
                    "updated_at",
                ]
            )

            for week_index, raw_amount in settings["payments"]:
                week = weeks[week_index]
                reference = (
                    f"DEMO-{year.year}-{member.bahasha_number}-{key.upper()}-"
                    f"W{week.week_number:02d}"
                )
                if Contribution.objects.filter(reference_number=reference).exists():
                    continue
                contribution = Contribution(
                    reference_number=reference,
                    church=member.church,
                    member=member,
                    bahasha_number=member.bahasha_number,
                    financial_year=year,
                    contribution_week=week,
                    category=category,
                    amount=Decimal(raw_amount),
                    contribution_date=week.sunday_date,
                    source="MANUAL_ENTRY",
                    status="POSTED",
                    posted_by=member.user,
                    remarks="Mobile demonstration contribution.",
                )
                contribution.full_clean()
                contribution.save()
                created_count += 1

            contributed = (
                Contribution.objects.filter(
                    member=member,
                    church=member.church,
                    financial_year=year,
                    category=category,
                    status="POSTED",
                ).aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )
            target, _ = MemberAnnualTarget.objects.get_or_create(
                member=member,
                church=member.church,
                financial_year=year,
                category=category,
                defaults={"target_amount": settings["target"]},
            )
            target.target_amount = settings["target"]
            target.contributed_amount = contributed
            target.full_clean()
            target.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Mobile demo data ready for {member.user.username}: "
                f"{created_count} contributions created."
            )
        )
