import uuid

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ExcelUpload
from .serializers import ExcelUploadSerializer
from .services import process_excel_upload, approve_excel_upload


class ExcelUploadViewSet(viewsets.ModelViewSet):
    queryset = ExcelUpload.objects.all().order_by("-uploaded_at")
    serializer_class = ExcelUploadSerializer

    def perform_create(self, serializer):
        uploaded_file = self.request.FILES.get("file")

        upload = serializer.save(
            uploaded_by=self.request.user,
            file_name=uploaded_file.name if uploaded_file else "",
            upload_reference=f"UPL-{uuid.uuid4().hex[:10].upper()}",
        )

        process_excel_upload(upload)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        upload = self.get_object()

        if upload.status != "VALIDATED":
            return Response(
                {
                    "message": "Only validated uploads can be approved.",
                    "current_status": upload.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        approve_excel_upload(upload, request.user)

        return Response(
            {
                "message": "Excel upload approved and contributions posted successfully.",
                "upload_id": upload.id,
                "status": upload.status,
            },
            status=status.HTTP_200_OK,
        )