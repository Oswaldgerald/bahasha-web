from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from annual_targets.models import MemberAnnualTarget
from categories.models import ContributionCategory
from churches.models import Church
from contribution_weeks.models import ContributionWeek
from financial_years.models import FinancialYear
from members.models import Member
from users.models import User

from .models import Contribution
from .services import contribution_target_key, save_contribution


class ContributionServiceTests(TestCase):
    def setUp(self):
        self.church = Church.objects.create(
            church_code="CH-CONTRIB",
            church_name="Contribution Test Church",
        )
        self.admin = User.objects.create_user(
            username="contribution-admin",
            password="strong-test-password",
            full_name="Contribution Administrator",
            phone_number="255700000020",
            role="ADMIN",
            church=self.church,
        )
        member_user = User.objects.create_user(
            username="contribution-member",
            password="strong-test-password",
            full_name="Contribution Member",
            phone_number="255700000021",
            role="MEMBER",
            church=self.church,
        )
        self.member = Member.objects.create(
            user=member_user,
            church=self.church,
            bahasha_number="B-CONTRIB",
            approval_status="APPROVED",
        )
        self.financial_year = FinancialYear.objects.create(
            church=self.church,
            year=2026,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.week = ContributionWeek.objects.create(
            church=self.church,
            financial_year=self.financial_year,
            week_number=1,
            sunday_date=date(2026, 1, 4),
        )
        self.category = ContributionCategory.objects.create(
            church=self.church,
            name="Contribution Test Offering",
            code="CONTRIB-TEST",
        )
        self.target = MemberAnnualTarget.objects.create(
            member=self.member,
            church=self.church,
            financial_year=self.financial_year,
            category=self.category,
            target_amount=Decimal("1000.00"),
        )

    def contribution(self, amount="250.00", status="POSTED", reference="TEST-001"):
        return Contribution(
            church=self.church,
            member=self.member,
            financial_year=self.financial_year,
            contribution_week=self.week,
            category=self.category,
            amount=Decimal(amount),
            contribution_date=self.week.sunday_date,
            source="MANUAL_ENTRY",
            status=status,
            reference_number=reference,
            posted_by=self.admin,
        )

    def test_save_derives_bahasha_number_and_recalculates_target(self):
        contribution = save_contribution(self.contribution())

        self.target.refresh_from_db()
        self.assertEqual(contribution.bahasha_number, self.member.bahasha_number)
        self.assertEqual(self.target.contributed_amount, Decimal("250.00"))
        self.assertEqual(self.target.remaining_amount, Decimal("750.00"))

    def test_edit_recalculates_target_without_double_counting(self):
        contribution = save_contribution(self.contribution())
        previous_key = contribution_target_key(contribution)
        contribution.amount = Decimal("400.00")

        save_contribution(contribution, previous_key)

        self.target.refresh_from_db()
        self.assertEqual(self.target.contributed_amount, Decimal("400.00"))

    def test_reversed_contribution_is_removed_from_target_total(self):
        contribution = save_contribution(self.contribution())
        previous_key = contribution_target_key(contribution)
        contribution.status = "REVERSED"

        save_contribution(contribution, previous_key)

        self.target.refresh_from_db()
        self.assertEqual(self.target.contributed_amount, Decimal("0.00"))

    def test_non_positive_amount_is_rejected(self):
        with self.assertRaises(ValidationError):
            save_contribution(self.contribution(amount="0.00"))

    def test_cross_church_member_is_rejected(self):
        other_church = Church.objects.create(
            church_code="CH-OTHER",
            church_name="Other Church",
        )
        contribution = self.contribution()
        contribution.church = other_church

        with self.assertRaises(ValidationError):
            save_contribution(contribution)

    def test_manual_web_entry_uses_the_shared_contribution_service(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("web_contribution_create"),
            {
                "church": self.church.id,
                "member": self.member.id,
                "financial_year": self.financial_year.id,
                "contribution_week": self.week.id,
                "category": self.category.id,
                "amount": "125.00",
                "contribution_date": self.week.sunday_date.isoformat(),
                "status": "POSTED",
                "remarks": "Web entry test",
            },
        )

        self.assertRedirects(response, reverse("web_contributions"))
        contribution = Contribution.objects.get(reference_number__startswith="MANUAL-")
        self.assertEqual(contribution.source, "MANUAL_ENTRY")
        self.assertEqual(contribution.bahasha_number, self.member.bahasha_number)
        self.target.refresh_from_db()
        self.assertEqual(self.target.contributed_amount, Decimal("125.00"))

    def test_contribution_workspace_combines_entry_and_upload_workflows(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("web_contributions"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Contributions workspace"')
        self.assertContains(response, "Record payment")
        self.assertContains(response, "Upload Excel")
        self.assertContains(response, "Upload history")
        self.assertNotContains(response, 'id="nav-uploads"')

    def test_manual_entry_can_be_submitted_from_contribution_workspace(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("web_contributions"),
            {
                "entry_mode": "manual",
                "church": self.church.id,
                "member": self.member.id,
                "financial_year": self.financial_year.id,
                "contribution_week": self.week.id,
                "category": self.category.id,
                "amount": "175.00",
                "contribution_date": self.week.sunday_date.isoformat(),
                "status": "POSTED",
                "remarks": "Unified workspace entry",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('web_contributions')}?tab=records",
        )
        contribution = Contribution.objects.get(
            remarks="Unified workspace entry",
        )
        self.assertEqual(contribution.bahasha_number, self.member.bahasha_number)

    def test_workspace_shows_the_selected_upload_form(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("web_contributions"),
            {"tab": "upload"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="entry_mode" value="upload"')
        self.assertContains(response, 'data-contribution-file-input="true"')
        self.assertContains(response, "Drop your Excel file here")

    def test_workspace_filters_contributions_by_category(self):
        first_contribution = self.contribution(
            reference="FILTER-FIRST",
        )
        save_contribution(first_contribution)
        other_category = ContributionCategory.objects.create(
            church=self.church,
            name="Building Fund",
            code="BUILD-FILTER",
        )
        other_contribution = self.contribution(
            amount="300.00",
            reference="FILTER-SECOND",
        )
        other_contribution.category = other_category
        save_contribution(other_contribution)
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("web_contributions"),
            {"tab": "records", "category": other_category.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["contributions"].paginator.count, 1)
        self.assertEqual(
            response.context["contributions"][0].reference_number,
            "FILTER-SECOND",
        )
        self.assertContains(response, 'name="contribution_week"')
        self.assertContains(response, 'name="category"')
        self.assertContains(response, 'name="status"')
