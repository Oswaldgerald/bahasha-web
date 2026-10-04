from django.urls import path, include
from . import views


urlpatterns = [


    path("dashboard/", views.dashboard, name="web_dashboard"),

    # Member Management
    path("members/", views.member_list, name="web_members"),
    path("members/create/", views.member_create, name="web_member_create"),
    path("members/jumuiya-options/", views.member_jumuiya_options, name="web_member_jumuiya_options"),
    path("members/<int:member_id>/edit/", views.member_edit, name="web_member_edit"),
    path("members/<int:member_id>/approve/", views.approve_member, name="web_member_approve"),
    path("members/<int:member_id>/reject/", views.reject_member, name="web_member_reject"),
    path("members/<int:member_id>/", views.member_detail, name="web_member_detail"),

    # Category Management
    path("categories/", views.category_list, name="web_categories"),
    path("categories/create/", views.category_create, name="web_category_create"),
    path("categories/<int:category_id>/edit/", views.category_edit, name="web_category_edit"),

    # Financial Years Management
    path("financial-years/", views.financial_year_list, name="web_financial_years"),
    path("financial-years/create/", views.financial_year_create, name="web_financial_year_create"),
    path("financial-years/<int:financial_year_id>/edit/", views.financial_year_edit, name="web_financial_year_edit"),

    # Contribution Weeks Management
    path("contribution-weeks/", views.contribution_week_list, name="web_contribution_weeks"),
    path("contribution-weeks/create/", views.contribution_week_create, name="web_contribution_week_create"),
    path("contribution-weeks/<int:week_id>/edit/", views.contribution_week_edit, name="web_contribution_week_edit"),
    path("contribution-weeks/<int:week_id>/activate/", views.contribution_week_activate, name="web_contribution_week_activate"),
    path("contribution-weeks/<int:week_id>/close/", views.contribution_week_close, name="web_contribution_week_close"),
    path("contribution-weeks/generate/",views.contribution_week_generate,name="web_contribution_week_generate"),
    #  Member Annual Targets
    path("annual-targets/", views.annual_target_list, name="web_annual_targets"),
    path("annual-targets/create/", views.annual_target_create, name="web_annual_target_create"),
    path("annual-targets/<int:target_id>/edit/", views.annual_target_edit, name="web_annual_target_edit"),
    # Contributions Management
    path("contributions/", views.contribution_list, name="web_contributions"),
    path("contributions/create/", views.contribution_create, name="web_contribution_create"),
    path("contributions/<int:contribution_id>/edit/", views.contribution_edit, name="web_contribution_edit"),
# Excel Uploads
    path("excel-uploads/", views.excel_upload_list, name="web_excel_uploads"),
    path("excel-uploads/create/", views.excel_upload_create, name="web_excel_upload_create"),
    path("excel-uploads/<int:upload_id>/", views.excel_upload_detail, name="web_excel_upload_detail"),
    path("excel-uploads/<int:upload_id>/approve/", views.excel_upload_approve, name="web_excel_upload_approve"),
# Summary and Reports
    path("reports/contribution-summary/", views.contribution_summary_report, name="web_contribution_summary_report"),
    path("reports/member-statement/", views.member_statement_report, name="web_member_statement_report"),
    path("reports/weekly-collection/", views.weekly_collection_report, name="web_weekly_collection_report"),
# Jumuiya Management
    path("jumuiya/", views.jumuiya_list, name="web_jumuiya"),
    path("jumuiya/create/", views.jumuiya_create, name="web_jumuiya_create"),
    path("jumuiya/<int:jumuiya_id>/edit/", views.jumuiya_edit, name="web_jumuiya_edit"),
# User Management
    path("users/",views.user_list,name="web_users"),
    path("users/create/",views.user_create,name="web_user_create"),
    path("users/<int:user_id>/edit/",views.user_edit,name="web_user_edit"),
    path("users/<int:user_id>/reset-password/",views.user_reset_password,name="web_user_reset_password"),

# Access Control
    path("users/<int:user_id>/activate/", views.user_activate, name="web_user_activate"),
    path("users/<int:user_id>/deactivate/", views.user_deactivate, name="web_user_deactivate"),
    path("churches/", views.church_list, name="web_churches"),
    path("churches/create/", views.church_create, name="web_church_create"),
    path("churches/<int:church_id>/edit/", views.church_edit, name="web_church_edit"),

    path("audit-logs/", views.audit_log_list, name="web_audit_logs"),

    # Notifications
    path("notifications/", views.notification_list, name="web_notifications"),
    path("notifications/create/", views.notification_create, name="web_notification_create"),

    # auth
    path("", include("users.urls")),
    path("profile/", views.profile_view, name="web_profile"),
    path("profile/picture/", views.profile_picture_view, name="web_profile_picture"),
    path("profile/change-password/", views.change_password_view, name="web_change_password"),
    ]
