from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from churches.models import Church
from contribution_weeks.models import ContributionWeek
from financial_years.models import FinancialYear
from users.models import User


class ContributionWeekListTests(TestCase):
    def setUp(self):
        self.church = Church.objects.create(
            church_code="WEEK-01",
            church_name="Week Test Church",
        )
        self.user = User.objects.create_user(
            username="week-admin",
            password="strong-test-password",
            full_name="Week Administrator",
            phone_number="255700000041",
            role="ADMIN",
            church=self.church,
        )
        self.financial_year = FinancialYear.objects.create(
            church=self.church,
            year=2026,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        first_sunday = date(2026, 1, 4)
        for offset in range(21):
            ContributionWeek.objects.create(
                church=self.church,
                financial_year=self.financial_year,
                week_number=offset + 1,
                sunday_date=first_sunday + timedelta(days=offset * 7),
            )
        self.client.force_login(self.user)

    def test_week_list_places_most_recent_week_first_and_paginates(self):
        response = self.client.get(reverse("web_contribution_weeks"))

        self.assertEqual(response.status_code, 200)
        weeks = response.context["weeks"]
        self.assertEqual(weeks.paginator.num_pages, 2)
        self.assertEqual(weeks[0].week_number, 21)
        self.assertContains(response, "Showing 1-20")
        self.assertContains(response, "of 21 records")
        self.assertContains(response, "page=2")

        second_page = self.client.get(
            reverse("web_contribution_weeks"),
            {"page": 2},
        )
        self.assertEqual(second_page.context["weeks"][0].week_number, 1)

    @patch("contribution_weeks.views.timezone.localdate")
    def test_current_calendar_week_precedes_future_weeks(self, localdate):
        localdate.return_value = date(2026, 10, 9)
        current_week = ContributionWeek.objects.create(
            church=self.church,
            financial_year=self.financial_year,
            week_number=40,
            sunday_date=date(2026, 10, 4),
        )
        ContributionWeek.objects.create(
            church=self.church,
            financial_year=self.financial_year,
            week_number=52,
            sunday_date=date(2026, 12, 27),
        )

        response = self.client.get(reverse("web_contribution_weeks"))

        self.assertEqual(response.context["weeks"][0], current_week)

    @patch("contribution_weeks.views.timezone.localdate")
    def test_explicitly_active_week_has_highest_priority(self, localdate):
        localdate.return_value = date(2026, 10, 9)
        active_week = ContributionWeek.objects.create(
            church=self.church,
            financial_year=self.financial_year,
            week_number=30,
            sunday_date=date(2026, 7, 26),
            is_active=True,
        )
        ContributionWeek.objects.create(
            church=self.church,
            financial_year=self.financial_year,
            week_number=40,
            sunday_date=date(2026, 10, 4),
        )

        response = self.client.get(reverse("web_contribution_weeks"))

        self.assertEqual(response.context["weeks"][0], active_week)
