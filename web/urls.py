from django.urls import include, path

from annual_targets import views as annual_target_views
from audit_logs import views as audit_log_views
from categories import views as category_views
from churches import views as church_views
from contribution_weeks import views as contribution_week_views
from contributions import views as contribution_views
from dashboard import views as dashboard_views
from excel_uploads import views as excel_upload_views
from financial_years import views as financial_year_views
from jumuiya import views as jumuiya_views
from members import views as member_views
from notifications import views as notification_views
from reports import views as report_views
from users import views as user_views


urlpatterns = [
    path("dashboard/", dashboard_views.dashboard, name="web_dashboard"),
    # Member Management
    path("members/", member_views.member_list, name="web_members"),
    path("members/create/", member_views.member_create, name="web_member_create"),
    path(
        "members/import-csv/",
        member_views.member_csv_import,
        name="web_member_csv_import",
    ),
    path(
        "members/export-csv/",
        member_views.member_csv_export,
        name="web_member_csv_export",
    ),
    path(
        "members/csv-template/",
        member_views.member_csv_template,
        name="web_member_csv_template",
    ),
    path(
        "members/jumuiya-options/",
        member_views.member_jumuiya_options,
        name="web_member_jumuiya_options",
    ),
    path(
        "members/<int:member_id>/edit/",
        member_views.member_edit,
        name="web_member_edit",
    ),
    path(
        "members/<int:member_id>/picture/",
        member_views.member_profile_picture,
        name="web_member_profile_picture",
    ),
    path(
        "members/<int:member_id>/approve/",
        member_views.approve_member,
        name="web_member_approve",
    ),
    path(
        "members/<int:member_id>/reject/",
        member_views.reject_member,
        name="web_member_reject",
    ),
    path(
        "members/<int:member_id>/", member_views.member_detail, name="web_member_detail"
    ),
    # Category Management
    path("categories/", category_views.category_list, name="web_categories"),
    path(
        "categories/create/", category_views.category_create, name="web_category_create"
    ),
    path(
        "categories/<int:category_id>/edit/",
        category_views.category_edit,
        name="web_category_edit",
    ),
    # Financial Years Management
    path(
        "financial-years/",
        financial_year_views.financial_year_list,
        name="web_financial_years",
    ),
    path(
        "financial-years/create/",
        financial_year_views.financial_year_create,
        name="web_financial_year_create",
    ),
    path(
        "financial-years/<int:financial_year_id>/edit/",
        financial_year_views.financial_year_edit,
        name="web_financial_year_edit",
    ),
    # Contribution Weeks Management
    path(
        "contribution-weeks/",
        contribution_week_views.contribution_week_list,
        name="web_contribution_weeks",
    ),
    path(
        "contribution-weeks/create/",
        contribution_week_views.contribution_week_create,
        name="web_contribution_week_create",
    ),
    path(
        "contribution-weeks/<int:week_id>/edit/",
        contribution_week_views.contribution_week_edit,
        name="web_contribution_week_edit",
    ),
    path(
        "contribution-weeks/<int:week_id>/activate/",
        contribution_week_views.contribution_week_activate,
        name="web_contribution_week_activate",
    ),
    path(
        "contribution-weeks/<int:week_id>/close/",
        contribution_week_views.contribution_week_close,
        name="web_contribution_week_close",
    ),
    path(
        "contribution-weeks/generate/",
        contribution_week_views.contribution_week_generate,
        name="web_contribution_week_generate",
    ),
    #  Member Annual Targets
    path(
        "annual-targets/",
        annual_target_views.annual_target_list,
        name="web_annual_targets",
    ),
    path(
        "annual-targets/create/",
        annual_target_views.annual_target_create,
        name="web_annual_target_create",
    ),
    path(
        "annual-targets/<int:target_id>/edit/",
        annual_target_views.annual_target_edit,
        name="web_annual_target_edit",
    ),
    # Contributions Management
    path(
        "contributions/", contribution_views.contribution_list, name="web_contributions"
    ),
    path(
        "contributions/create/",
        contribution_views.contribution_create,
        name="web_contribution_create",
    ),
    path(
        "contributions/<int:contribution_id>/edit/",
        contribution_views.contribution_edit,
        name="web_contribution_edit",
    ),
    # Excel Uploads
    path(
        "excel-uploads/", excel_upload_views.excel_upload_list, name="web_excel_uploads"
    ),
    path(
        "excel-uploads/create/",
        excel_upload_views.excel_upload_create,
        name="web_excel_upload_create",
    ),
    path(
        "excel-uploads/<int:upload_id>/",
        excel_upload_views.excel_upload_detail,
        name="web_excel_upload_detail",
    ),
    path(
        "excel-uploads/<int:upload_id>/approve/",
        excel_upload_views.excel_upload_approve,
        name="web_excel_upload_approve",
    ),
    # Summary and Reports
    path(
        "reports/contribution-summary/",
        report_views.contribution_summary_report,
        name="web_contribution_summary_report",
    ),
    path(
        "reports/member-statement/",
        report_views.member_statement_report,
        name="web_member_statement_report",
    ),
    path(
        "reports/weekly-collection/",
        report_views.weekly_collection_report,
        name="web_weekly_collection_report",
    ),
    # Jumuiya Management
    path("jumuiya/", jumuiya_views.jumuiya_list, name="web_jumuiya"),
    path("jumuiya/create/", jumuiya_views.jumuiya_create, name="web_jumuiya_create"),
    path(
        "jumuiya/<int:jumuiya_id>/edit/",
        jumuiya_views.jumuiya_edit,
        name="web_jumuiya_edit",
    ),
    # User Management
    path("users/", user_views.user_list, name="web_users"),
    path("users/create/", user_views.user_create, name="web_user_create"),
    path("users/<int:user_id>/edit/", user_views.user_edit, name="web_user_edit"),
    path(
        "users/<int:user_id>/reset-password/",
        user_views.user_reset_password,
        name="web_user_reset_password",
    ),
    # Access Control
    path(
        "users/<int:user_id>/activate/",
        user_views.user_activate,
        name="web_user_activate",
    ),
    path(
        "users/<int:user_id>/deactivate/",
        user_views.user_deactivate,
        name="web_user_deactivate",
    ),
    path("churches/", church_views.church_list, name="web_churches"),
    path("churches/create/", church_views.church_create, name="web_church_create"),
    path(
        "churches/<int:church_id>/edit/",
        church_views.church_edit,
        name="web_church_edit",
    ),
    path(
        "church-groups/",
        church_views.church_group_list,
        name="web_church_groups",
    ),
    path(
        "church-groups/create/",
        church_views.church_group_create,
        name="web_church_group_create",
    ),
    path(
        "church-groups/<int:group_id>/edit/",
        church_views.church_group_edit,
        name="web_church_group_edit",
    ),
    path("audit-logs/", audit_log_views.audit_log_list, name="web_audit_logs"),
    # Notifications
    path(
        "notifications/", notification_views.notification_list, name="web_notifications"
    ),
    path(
        "notifications/create/",
        notification_views.notification_create,
        name="web_notification_create",
    ),
    # auth
    path("", include("users.urls")),
    path("profile/", user_views.profile_view, name="web_profile"),
    path(
        "profile/picture/", user_views.profile_picture_view, name="web_profile_picture"
    ),
    path(
        "profile/change-password/",
        user_views.change_password_view,
        name="web_change_password",
    ),
]
