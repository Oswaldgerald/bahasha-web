from datetime import date
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook

from categories.models import ContributionCategory
from churches.models import Church
from contribution_weeks.models import ContributionWeek
from excel_uploads.models import ExcelUpload
from excel_uploads.services import process_excel_upload
from financial_years.models import FinancialYear
from members.models import Member
from users.models import User


class ExcelUploadProcessingTests(TestCase):
    def setUp(self):
        self.church = Church.objects.create(
            church_code="CH-004",
            church_name="Import Test Church",
        )
        self.admin = User.objects.create_user(
            username="import-admin",
            password="strong-test-password",
            full_name="Import Administrator",
            phone_number="255700000008",
            role="ADMIN",
            church=self.church,
        )
        member_user = User.objects.create_user(
            username="import-member",
            password="strong-test-password",
            full_name="Import Member",
            phone_number="255700000009",
            role="MEMBER",
            church=self.church,
        )
        Member.objects.create(
            user=member_user,
            church=self.church,
            bahasha_number="B-004",
            approval_status="APPROVED",
        )
        financial_year = FinancialYear.objects.create(
            church=self.church,
            year=2026,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        week = ContributionWeek.objects.create(
            church=self.church,
            financial_year=financial_year,
            week_number=1,
            sunday_date=date(2026, 1, 4),
        )
        category = ContributionCategory.objects.create(
            name="Import Offering",
            code="IMPORT",
        )

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Bahasha Number", "Amount"])
        sheet.append(["B-004", 125])
        sheet.append(["B-004", "invalid"])
        content = BytesIO()
        workbook.save(content)

        self.upload = ExcelUpload.objects.create(
            church=self.church,
            financial_year=financial_year,
            contribution_week=week,
            selected_category=category,
            uploaded_by=self.admin,
            file=SimpleUploadedFile(
                "import.xlsx",
                content.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            file_name="import.xlsx",
            upload_reference="UPL-PROCESS",
        )

    def test_processing_marks_bad_amount_without_crashing(self):
        process_excel_upload(self.upload)

        self.upload.refresh_from_db()
        self.assertEqual(self.upload.total_rows, 2)
        self.assertEqual(self.upload.valid_rows, 1)
        self.assertEqual(self.upload.failed_rows, 1)
        self.assertEqual(self.upload.total_amount, Decimal("125.00"))
        self.assertEqual(self.upload.status, "FAILED")

    def test_reprocessing_replaces_existing_validation_rows(self):
        process_excel_upload(self.upload)
        process_excel_upload(self.upload)

        self.assertEqual(self.upload.rows.count(), 2)

# Create your tests here.
