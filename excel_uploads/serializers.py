from rest_framework import serializers
from .models import ExcelUpload, ExcelUploadRow


class ExcelUploadRowSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()

    class Meta:
        model = ExcelUploadRow
        fields = [
            "id",
            "row_number",
            "bahasha_number",
            "amount",
            "resolved_member",
            "member_name",
            "validation_status",
            "error_message",
            "created_at",
        ]

    def get_member_name(self, obj):
        if obj.resolved_member:
            return obj.resolved_member.user.full_name
        return None


class ExcelUploadSerializer(serializers.ModelSerializer):
    rows = ExcelUploadRowSerializer(many=True, read_only=True)

    class Meta:
        model = ExcelUpload
        fields = [
            "id",
            "church",
            "financial_year",
            "contribution_week",
            "selected_category",
            "uploaded_by",
            "file",
            "file_name",
            "upload_reference",
            "total_rows",
            "valid_rows",
            "failed_rows",
            "total_amount",
            "status",
            "approved_by",
            "approved_at",
            "uploaded_at",
            "rows",
        ]

        read_only_fields = [
            "uploaded_by",
            "file_name",
            "upload_reference",
            "total_rows",
            "valid_rows",
            "failed_rows",
            "total_amount",
            "status",
            "approved_by",
            "approved_at",
            "uploaded_at",
        ]