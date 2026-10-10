from django.contrib import admin

from config.admin_mixins import RowDeleteActionMixin

from .models import ExcelUpload, ExcelUploadRow


class ExcelUploadRowInline(admin.TabularInline):
    model = ExcelUploadRow
    extra = 0
    readonly_fields = (
        "row_number",
        "bahasha_number",
        "amount",
        "resolved_member",
        "validation_status",
        "error_message",
        "created_at",
    )


@admin.register(ExcelUpload)
class ExcelUploadAdmin(RowDeleteActionMixin, admin.ModelAdmin):
    list_display = (
        "upload_reference",
        "church",
        "financial_year",
        "contribution_week",
        "selected_category",
        "status",
        "total_rows",
        "valid_rows",
        "failed_rows",
        "total_amount",
        "uploaded_by",
        "uploaded_at",
    )

    search_fields = (
        "upload_reference",
        "file_name",
        "church__church_name",
    )

    list_filter = (
        "church",
        "financial_year",
        "selected_category",
        "status",
    )

    readonly_fields = (
        "uploaded_at",
    )

    inlines = [ExcelUploadRowInline]


@admin.register(ExcelUploadRow)
class ExcelUploadRowAdmin(RowDeleteActionMixin, admin.ModelAdmin):
    list_display = (
        "upload",
        "row_number",
        "bahasha_number",
        "amount",
        "resolved_member",
        "validation_status",
    )

    search_fields = (
        "bahasha_number",
        "resolved_member__user__full_name",
    )

    list_filter = (
        "validation_status",
    )
