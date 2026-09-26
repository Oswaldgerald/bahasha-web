from datetime import date
from decimal import Decimal

from django.test import TestCase

from annual_targets.models import MemberAnnualTarget
from categories.models import ContributionCategory
from churches.models import Church
from financial_years.models import FinancialYear
from members.models import Member
from users.models import User


class MemberAnnualTargetTests(TestCase):
    def setUp(self):
        self.church = Church.objects.create(
            church_code="CH-001",
            church_name="Test Church",
        )
        user = User.objects.create_user(
            username="member",
            password="strong-test-password",
            full_name="Test Member",
            phone_number="255700000003",
            role="MEMBER",
            church=self.church,
        )
        self.member = Member.objects.create(
            user=user,
            church=self.church,
            bahasha_number="B-001",
            approval_status="APPROVED",
        )
        self.financial_year = FinancialYear.objects.create(
            church=self.church,
            year=2026,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.category = ContributionCategory.objects.create(
            name="Weekly Offering",
            code="WEEKLY",
        )

    def test_save_calculates_remaining_amount_and_percentage(self):
        target = MemberAnnualTarget.objects.create(
            member=self.member,
            church=self.church,
            financial_year=self.financial_year,
            category=self.category,
            target_amount=Decimal("1000.00"),
            contributed_amount=Decimal("250.00"),
        )

        self.assertEqual(target.remaining_amount, Decimal("750.00"))
        self.assertEqual(target.completion_percentage, Decimal("25.00"))

# Create your tests here.
