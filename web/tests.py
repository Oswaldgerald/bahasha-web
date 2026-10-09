from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import resolve, reverse

from audit_logs.models import AuditLog
from categories.models import ContributionCategory
from churches.models import Church
from contribution_weeks.models import ContributionWeek
from contributions.models import Contribution
from excel_uploads.models import ExcelUpload, ExcelUploadRow
from financial_years.models import FinancialYear
from members.models import Member
from users.models import User
from web.forms import ExcelUploadForm


class StateChangingViewTests(TestCase):
    def setUp(self):
        self.church = Church.objects.create(
            church_code="CH-002",
            church_name="Web Test Church",
        )
        self.admin = User.objects.create_user(
            username="web-admin",
            password="strong-test-password",
            full_name="Web Administrator",
            phone_number="255700000004",
            role="ADMIN",
            church=self.church,
        )
        member_user = User.objects.create_user(
            username="pending-member",
            password="strong-test-password",
            full_name="Pending Member",
            phone_number="255700000005",
            role="MEMBER",
            church=self.church,
        )
        self.member = Member.objects.create(
            user=member_user,
            church=self.church,
            bahasha_number="B-002",
        )
        self.client.force_login(self.admin)

    def test_member_approval_rejects_get_and_accepts_post(self):
        url = reverse("web_member_approve", args=[self.member.id])

        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)

        self.member.refresh_from_db()
        self.assertEqual(self.member.approval_status, "APPROVED")
        self.assertIsNotNone(self.member.approved_at)


class ExcelApprovalTests(TestCase):
    def setUp(self):
        self.church = Church.objects.create(
            church_code="CH-003",
            church_name="Excel Test Church",
        )
        self.admin = User.objects.create_user(
            username="excel-admin",
            password="strong-test-password",
            full_name="Excel Administrator",
            phone_number="255700000006",
            role="ADMIN",
            church=self.church,
        )
        member_user = User.objects.create_user(
            username="excel-member",
            password="strong-test-password",
            full_name="Excel Member",
            phone_number="255700000007",
            role="MEMBER",
            church=self.church,
        )
        self.member = Member.objects.create(
            user=member_user,
            church=self.church,
            bahasha_number="B-003",
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
            name="Excel Offering",
            code="EXCEL",
        )
        self.upload = ExcelUpload.objects.create(
            church=self.church,
            financial_year=self.financial_year,
            contribution_week=self.week,
            selected_category=self.category,
            uploaded_by=self.admin,
            file=SimpleUploadedFile("offering.xlsx", b"test"),
            file_name="offering.xlsx",
            upload_reference="UPL-TEST",
            total_rows=1,
            valid_rows=1,
            total_amount=Decimal("150.00"),
            status="VALIDATED",
        )
        ExcelUploadRow.objects.create(
            upload=self.upload,
            row_number=2,
            bahasha_number=self.member.bahasha_number,
            amount=Decimal("150.00"),
            resolved_member=self.member,
            validation_status="VALID",
        )
        self.client.force_login(self.admin)

    def test_approval_posts_contribution_and_audit_log(self):
        url = reverse("web_excel_upload_approve", args=[self.upload.id])

        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url)

        self.assertRedirects(
            response,
            reverse("web_excel_upload_detail", args=[self.upload.id]),
        )
        self.upload.refresh_from_db()
        self.assertEqual(self.upload.status, "POSTED")
        self.assertEqual(Contribution.objects.count(), 1)
        self.assertTrue(
            AuditLog.objects.filter(
                action="EXCEL_APPROVED",
                entity_id=str(self.upload.id),
            ).exists()
        )

    def test_contribution_upload_view_uses_custom_bilingual_file_control(self):
        response = self.client.get(reverse("web_excel_upload_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-contribution-file-input="true"')
        self.assertContains(response, "Drop your Excel file here")
        self.assertContains(response, "Buruta faili hapa")
        self.assertContains(response, "Maximum 5 MB")

    def test_contribution_upload_form_rejects_non_xlsx_file(self):
        form = ExcelUploadForm(
            data={
                "church": self.church.id,
                "financial_year": self.financial_year.id,
                "contribution_week": self.week.id,
                "selected_category": self.category.id,
            },
            files={
                "file": SimpleUploadedFile(
                    "contributions.csv",
                    b"Bahasha Number,Amount\nB-003,100\n",
                    content_type="text/csv",
                )
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn(".xlsx extension", form.errors["file"][0])


class CurrentPageHeaderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="navigation-admin",
            password="strong-test-password",
            full_name="Navigation Administrator",
            phone_number="255700000030",
            role="ADMIN",
        )
        self.client.force_login(self.user)

    def test_topbar_reflects_the_current_page(self):
        pages = [
            ("web_dashboard", "Dashboard"),
            ("web_categories", "Contribution Categories"),
            ("web_contributions", "Contributions"),
            ("web_excel_uploads", "Contribution Uploads"),
            ("web_profile", "My Profile"),
        ]

        for route_name, title in pages:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'data-page-title="{title}"')

    def test_report_pages_use_the_shared_report_interface(self):
        report_pages = [
            ("web_contribution_summary_report", "Contribution Summary"),
            ("web_member_statement_report", "Member Statement"),
            ("web_weekly_collection_report", "Weekly Collection"),
        ]

        for route_name, heading in report_pages:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'class="report-page"')
                self.assertContains(response, 'class="card report-filter-card"')
                self.assertContains(response, heading)


class ViewModuleOwnershipTests(TestCase):
    def test_web_routes_resolve_to_their_domain_modules(self):
        route_modules = {
            "web_dashboard": "dashboard.views",
            "web_members": "members.views",
            "web_categories": "categories.views",
            "web_financial_years": "financial_years.views",
            "web_contribution_weeks": "contribution_weeks.views",
            "web_annual_targets": "annual_targets.views",
            "web_contributions": "contributions.views",
            "web_excel_uploads": "excel_uploads.views",
            "web_contribution_summary_report": "reports.views",
            "web_member_statement_report": "reports.views",
            "web_weekly_collection_report": "reports.views",
            "web_jumuiya": "jumuiya.views",
            "web_users": "users.views",
            "web_churches": "churches.views",
            "web_church_groups": "churches.views",
            "web_audit_logs": "audit_logs.views",
            "web_notifications": "notifications.views",
            "web_profile": "users.views",
        }

        for route_name, expected_module in route_modules.items():
            with self.subTest(route_name=route_name):
                match = resolve(reverse(route_name))
                self.assertEqual(match.func.__module__, expected_module)
