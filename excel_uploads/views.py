from .models import ExcelUpload
from .serializers import ExcelUploadSerializer
from .services import process_excel_upload, approve_excel_upload
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.views.decorators.http import require_POST
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from audit_logs.services import create_audit_log
from web.forms import ExcelUploadForm


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


@login_required(login_url="login")
def excel_upload_list(request):
    uploads = ExcelUpload.objects.select_related(
        "church",
        "financial_year",
        "contribution_week",
        "selected_category",
        "uploaded_by",
        "approved_by",
    ).order_by("-uploaded_at")

    summary = uploads.aggregate(
        total=Count("id"),
        amount=Sum("total_amount", default=0),
    )

    return render(
        request,
        "excel_uploads/list.html",
        {"uploads": uploads, "summary": summary},
    )


@login_required(login_url="login")
def excel_upload_create(request):
    if request.method == "POST":
        form = ExcelUploadForm(request.POST, request.FILES)

        if form.is_valid():
            upload = form.save(commit=False)

            upload.uploaded_by = request.user
            upload.file_name = upload.file.name
            upload.upload_reference = f"UPL-{uuid.uuid4().hex[:10].upper()}"

            upload.save()

            process_excel_upload(upload)

            messages.success(
                request, "Contribution file uploaded and validated successfully."
            )
            return redirect("web_excel_upload_detail", upload_id=upload.id)
    else:
        form = ExcelUploadForm()

    return render(request, "excel_uploads/create.html", {"form": form})


@login_required(login_url="login")
def excel_upload_detail(request, upload_id):
    upload = get_object_or_404(
        ExcelUpload.objects.select_related(
            "church",
            "financial_year",
            "contribution_week",
            "selected_category",
            "uploaded_by",
            "approved_by",
        ),
        id=upload_id,
    )

    rows = upload.rows.select_related("resolved_member").all()

    return render(
        request, "excel_uploads/detail.html", {"upload": upload, "rows": rows}
    )


@login_required(login_url="login")
@require_POST
def excel_upload_approve(request, upload_id):
    upload = get_object_or_404(ExcelUpload, id=upload_id)

    if upload.status != "VALIDATED":
        messages.error(request, "Only validated uploads can be approved.")
        return redirect("web_excel_upload_detail", upload_id=upload.id)

    approve_excel_upload(upload, request.user)
    create_audit_log(
        user=request.user,
        church=upload.church,
        action="EXCEL_APPROVED",
        description=f"Approved contribution upload {upload.upload_reference}.",
        entity_type="ExcelUpload",
        entity_id=upload.id,
        request=request,
    )

    messages.success(request, "Upload approved and contributions posted successfully.")
    return redirect("web_excel_upload_detail", upload_id=upload.id)
