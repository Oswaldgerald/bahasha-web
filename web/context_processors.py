PAGE_METADATA = {
    "web_dashboard": ("Dashboard", "layout-dashboard"),
    "web_members": ("Members", "users-round"),
    "web_member_create": ("Add Member", "contact-round"),
    "web_member_edit": ("Edit Member", "settings"),
    "web_member_detail": ("Member Profile", "contact-round"),
    "web_member_csv_import": ("Upload Members", "file-up"),
    "web_categories": ("Contribution Categories", "tags"),
    "web_category_create": ("Add Category", "tags"),
    "web_category_edit": ("Edit Category", "settings"),
    "web_financial_years": ("Financial Years", "calendar-range"),
    "web_financial_year_create": ("Add Financial Year", "calendar-range"),
    "web_financial_year_edit": ("Edit Financial Year", "calendar-cog"),
    "web_contribution_weeks": ("Contribution Weeks", "calendar-days"),
    "web_contribution_week_create": ("Add Contribution Week", "calendar-days"),
    "web_contribution_week_edit": ("Edit Contribution Week", "calendar-cog"),
    "web_contribution_week_generate": ("Generate Contribution Weeks", "calendar-cog"),
    "web_annual_targets": ("Annual Targets", "target"),
    "web_annual_target_create": ("Add Annual Target", "target"),
    "web_annual_target_edit": ("Edit Annual Target", "settings"),
    "web_contributions": ("Contributions", "hand-coins"),
    "web_contribution_create": ("Record Contribution", "hand-coins"),
    "web_contribution_edit": ("Edit Contribution", "settings"),
    "web_excel_uploads": ("Excel Uploads", "file-spreadsheet"),
    "web_excel_upload_create": ("Upload Contributions", "file-spreadsheet"),
    "web_excel_upload_detail": ("Upload Details", "file-spreadsheet"),
    "web_contribution_summary_report": ("Contribution Summary", "chart-no-axes-combined"),
    "web_member_statement_report": ("Member Statements", "receipt-text"),
    "web_weekly_collection_report": ("Weekly Collection", "calendar-check-2"),
    "web_jumuiya": ("Jumuiya", "users-round"),
    "web_jumuiya_create": ("Add Jumuiya", "users-round"),
    "web_jumuiya_edit": ("Edit Jumuiya", "users-round"),
    "web_church_groups": ("Church Groups", "users-round"),
    "web_church_group_create": ("Add Church Group", "users-round"),
    "web_church_group_edit": ("Edit Church Group", "settings"),
    "web_users": ("Users & Roles", "shield-check"),
    "web_user_create": ("Add User", "users-round"),
    "web_user_edit": ("Edit User", "settings"),
    "web_user_reset_password": ("Reset Password", "key-round"),
    "web_churches": ("Churches", "landmark"),
    "web_church_create": ("Add Church", "landmark"),
    "web_church_edit": ("Edit Church", "landmark"),
    "web_audit_logs": ("Audit Logs", "scroll-text"),
    "web_notifications": ("Notifications", "bell"),
    "web_notification_create": ("Send Notification", "bell"),
    "web_profile": ("My Profile", "user-round"),
    "web_change_password": ("Change Password", "key-round"),
}

DEFAULT_PAGE = ("Bahasha", "landmark")


def current_page(request):
    resolver_match = getattr(request, "resolver_match", None)
    route_name = resolver_match.url_name if resolver_match else None
    title, icon = PAGE_METADATA.get(route_name, DEFAULT_PAGE)
    return {
        "current_page": {
            "title": title,
            "icon": icon,
        }
    }
