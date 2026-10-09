from .models import ExcelUpload
from .services import approve_excel_upload, create_excel_upload

from django.contrib import messages
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.views.decorators.http import require_POST

from audit_logs.services import create_audit_log
from web.forms import ExcelUploadForm
from web.pagination import paginate_queryset
from web.access import finance_management_required, scope_queryset_to_church


@finance_management_required
def excel_upload_list(request):
    uploads = ExcelUpload.objects.select_related(
        "church",
        "financial_year",
        "contribution_week",
        "selected_category",
        "uploaded_by",
        "approved_by",
    ).order_by("-uploaded_at")

    uploads = scope_queryset_to_church(uploads, request.user)
    summary = uploads.aggregate(
        total=Count("id"),
        amount=Sum("total_amount", default=0),
    )
    uploads = paginate_queryset(request, uploads)

    return render(
        request,
        "excel_uploads/list.html",
        {"uploads": uploads, "summary": summary},
    )


@finance_management_required
def excel_upload_create(request):
    if request.method == "POST":
        form = ExcelUploadForm(
            request.POST,
            request.FILES,
            request_user=request.user,
        )

        if form.is_valid():
            upload = create_excel_upload(form, request.user)

            messages.success(
                request, "Contribution file uploaded and validated successfully."
            )
            return redirect("web_excel_upload_detail", upload_id=upload.id)
    else:
        form = ExcelUploadForm(request_user=request.user)

    return render(request, "excel_uploads/create.html", {"form": form})


@finance_management_required
def excel_upload_detail(request, upload_id):
    upload = get_object_or_404(
        scope_queryset_to_church(
            ExcelUpload.objects.select_related(
                "church",
                "financial_year",
                "contribution_week",
                "selected_category",
                "uploaded_by",
                "approved_by",
            ),
            request.user,
        ),
        id=upload_id,
    )

    rows = upload.rows.select_related("resolved_member").all()

    return render(
        request, "excel_uploads/detail.html", {"upload": upload, "rows": rows}
    )


@finance_management_required
@require_POST
def excel_upload_approve(request, upload_id):
    upload = get_object_or_404(
        scope_queryset_to_church(ExcelUpload.objects.all(), request.user),
        id=upload_id,
    )

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
