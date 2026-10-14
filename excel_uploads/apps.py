from django.apps import AppConfig


class ExcelUploadsConfig(AppConfig):
    """Register contribution workbook imports with Django."""

    name = "excel_uploads"
    verbose_name = "Contribution Uploads"
