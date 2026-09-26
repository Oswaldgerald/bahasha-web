from django.db import models
from django.utils import timezone
from django.db.models import Sum
from django.shortcuts import render
from members.models import Member
from churches.models import Church
from .forms import ChurchForm
from members.models import Member
from contributions.models import Contribution
from excel_uploads.models import ExcelUpload
from financial_years.models import FinancialYear
from contribution_weeks.models import ContributionWeek
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from annual_targets.models import MemberAnnualTarget
from contributions.models import Contribution
from django.contrib import messages
from .forms import MemberCreateForm
from .forms import MemberEditForm
from categories.models import ContributionCategory
from .forms import ContributionCategoryForm
from financial_years.models import FinancialYear
from . forms import FinancialYearForm
from contribution_weeks.models import ContributionWeek
from .forms import ContributionWeekForm
from datetime import timedelta
from .forms import GenerateWeeksForm
from annual_targets.models import MemberAnnualTarget
from .forms import MemberAnnualTargetForm
from contributions.models import Contribution
from annual_targets.models import MemberAnnualTarget
from .forms import ContributionForm
import uuid
# Excel Uploads Management
from excel_uploads.models import ExcelUpload
from excel_uploads.services import process_excel_upload, approve_excel_upload
from .forms import ExcelUploadForm

from jumuiya.models import Jumuiya
from .forms import JumuiyaForm
from users.models import User
from .forms import UserForm
from audit_logs.models import AuditLog
from audit_logs.services import create_audit_log
from notifications.models import Notification
from .forms import NotificationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.http import require_POST
from .forms import ProfileUpdateForm


# Dashboard and Analysis
from django.db.models import Sum

from churches.models import Church
from members.models import Member
from contributions.models import Contribution
from excel_uploads.models import ExcelUpload
from financial_years.models import FinancialYear
from contribution_weeks.models import ContributionWeek
from annual_targets.models import MemberAnnualTarget


@login_required(login_url="login")
def dashboard(request):
    total_target = MemberAnnualTarget.objects.aggregate(
        total=Sum("target_amount")
    )["total"] or 0

    total_contributed = Contribution.objects.filter(
        status="POSTED"
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    if total_target > 0:
        overall_completion = round((total_contributed / total_target) * 100, 2)
    else:
        overall_completion = 0
    category_performance = list(
        MemberAnnualTarget.objects.values("category__name").annotate(
            total_target=Sum("target_amount"),
            total_contributed=Sum("contributed_amount"),
            total_remaining=Sum("remaining_amount"),
        ).order_by("category__name")
    )
    for item in category_performance:
        target = item["total_target"] or 0
        contributed = item["total_contributed"] or 0

        if target > 0:
            item["completion_percentage"] = round((contributed / target) * 100, 2)
        else:
            item["completion_percentage"] = 0

    recent_uploads = ExcelUpload.objects.select_related(
        "church",
        "financial_year",
        "contribution_week",
        "selected_category",
    ).order_by("-uploaded_at")[:5]

    recent_contributions = Contribution.objects.select_related(
        "member",
        "member__user",
        "category",
        "contribution_week",
    ).order_by("-created_at")[:5]

    context = {
        "total_churches": Church.objects.count(),
        "total_members": Member.objects.count(),
        "approved_members": Member.objects.filter(approval_status="APPROVED").count(),
        "pending_members": Member.objects.filter(approval_status="PENDING").count(),

        "total_contributions": Contribution.objects.filter(status="POSTED").count(),
        "total_contributed": total_contributed,
        "total_target": total_target,
        "overall_completion": overall_completion,

        "total_uploads": ExcelUpload.objects.count(),
        "pending_uploads": ExcelUpload.objects.filter(status="PENDING_VALIDATION").count(),
        "failed_uploads": ExcelUpload.objects.filter(status="FAILED").count(),

        "active_year": FinancialYear.objects.filter(is_active=True).first(),
        "active_week": ContributionWeek.objects.filter(is_active=True).first(),

        "recent_uploads": recent_uploads,
        "recent_contributions": recent_contributions,
        "category_performance": category_performance,
    }

    return render(request, "dashboard/index.html", context)
# User Management
@login_required(login_url="login")
def user_list(request):
    users = User.objects.select_related(
        "church"
    ).order_by("full_name")

    return render(
        request,
        "users/list.html",
        {
            "users": users
        }
    )
@login_required(login_url="login")
def user_create(request):
    if request.method == "POST":
        form = UserForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

            # Default password
            user.set_password("Password123")

            user.save()

            messages.success(
                request,
                "User created successfully."
            )

            return redirect("web_users")

    else:
        form = UserForm()

    return render(
        request,
        "users/create.html",
        {
            "form": form
        }
    )
@login_required(login_url="login")
def user_edit(request, user_id):
    user = get_object_or_404(
        User,
        id=user_id
    )

    if request.method == "POST":
        form = UserForm(
            request.POST,
            instance=user
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "User updated successfully."
            )

            return redirect("web_users")

    else:
        form = UserForm(instance=user)

    return render(
        request,
        "users/edit.html",
        {
            "form": form,
            "user_obj": user
        }
    )
@login_required(login_url="login")
def user_reset_password(request, user_id):
    user = get_object_or_404(
        User,
        id=user_id
    )

    user.set_password("Password123")
    user.save()
    create_audit_log(
    user=request.user,
    church=user.church,
    action="PASSWORD_RESET",
    description=f"Reset password for user {user.full_name}.",
    entity_type="User",
    entity_id=user.id,
    request=request,
)

    messages.success(
        request,
        f"Password reset for {user.full_name}"
    )

    return redirect("web_users")


@login_required(login_url="login")
def member_list(request):
    members = Member.objects.select_related(
        "user",
        "church",
        "jumuiya"
    ).all()
    return render(request, "members/member_list.html", {"members": members})

@login_required(login_url="login")
@require_POST
def approve_member(request, member_id):
    member = get_object_or_404(Member, id=member_id)

    member.approval_status = "APPROVED"
    member.approved_at = timezone.now()
    member.is_active = True
    member.save()
    create_audit_log(
    user=request.user,
    church=member.church,
    action="MEMBER_APPROVED",
    description=f"Approved member {member.user.full_name}.",
    entity_type="Member",
    entity_id=member.id,
    request=request,
)

    return redirect("web_members")

@login_required(login_url="login")
@require_POST
def reject_member(request, member_id):
    member = get_object_or_404(Member, id=member_id)

    member.approval_status = "REJECTED"
    member.is_active = False
    member.save()

    return redirect("web_members")

@login_required(login_url="login")
def member_detail(request, member_id):
    member = get_object_or_404(
        Member.objects.select_related(
            "user",
            "church",
            "jumuiya"
        ),
        id=member_id
    )

    targets = MemberAnnualTarget.objects.filter(
        member=member
    ).select_related(
        "category",
        "financial_year"
    )

    contributions = Contribution.objects.filter(
        member=member
    ).select_related(
        "category",
        "contribution_week"
    ).order_by("-contribution_date")[:20]

    total_contributed = sum(
        contribution.amount
        for contribution in contributions
    )

    context = {
        "member": member,
        "targets": targets,
        "contributions": contributions,
        "total_contributed": total_contributed,
    }

    return render(
        request,
        "members/member_detail.html",
        context
    )

@login_required(login_url="login")
def member_create(request):
    if request.method == "POST":
        form = MemberCreateForm(request.POST)

        if form.is_valid():
            member = form.save()
            create_audit_log(
                user=request.user,
                church=member.church,
                action="MEMBER_CREATED",
                description=f"Created member {member.user.full_name} with Bahasha number {member.bahasha_number}.",
                entity_type="Member",
                entity_id=member.id,
                request=request,
            )
            messages.success(request, "Member created successfully.")
            return redirect("web_members")
    else:
        form = MemberCreateForm()

    return render(request, "members/create.html", {
        "form": form
    })

@login_required(login_url="login")
def member_edit(request, member_id):
    member = get_object_or_404(
        Member.objects.select_related("user", "church", "jumuiya"),
        id=member_id
    )

    if request.method == "POST":
        form = MemberEditForm(request.POST, member=member)

        if form.is_valid():
            form.save()
            messages.success(request, "Member updated successfully.")
            return redirect("web_members")
    else:
        form = MemberEditForm(member=member)

    return render(request, "members/edit.html", {
        "form": form,
        "member": member
    })

@login_required(login_url="login")
def category_list(request):
    categories = ContributionCategory.objects.all()

    return render(request, "categories/list.html", {
        "categories": categories
    })


@login_required(login_url="login")
def category_create(request):
    if request.method == "POST":
        form = ContributionCategoryForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Contribution category created successfully.")
            return redirect("web_categories")
    else:
        form = ContributionCategoryForm()

    return render(request, "categories/create.html", {
        "form": form
    })

@login_required(login_url="login")
def category_edit(request, category_id):
    category = get_object_or_404(ContributionCategory, id=category_id)

    if request.method == "POST":
        form = ContributionCategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()
            messages.success(request, "Contribution category updated successfully.")
            return redirect("web_categories")
    else:
        form = ContributionCategoryForm(instance=category)

    return render(request, "categories/edit.html", {
        "form": form,
        "category": category
    })

@login_required(login_url="login")
def financial_year_list(request):
    financial_years = FinancialYear.objects.select_related("church").all()

    return render(request, "financial_years/list.html", {
        "financial_years": financial_years
    })


@login_required(login_url="login")
def financial_year_create(request):
    if request.method == "POST":
        form = FinancialYearForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Financial year created successfully.")
            return redirect("web_financial_years")
    else:
        form = FinancialYearForm()

    return render(request, "financial_years/create.html", {
        "form": form
    })

@login_required(login_url="login")
def financial_year_edit(request, financial_year_id):
    financial_year = get_object_or_404(FinancialYear, id=financial_year_id)

    if request.method == "POST":
        form = FinancialYearForm(request.POST, instance=financial_year)

        if form.is_valid():
            form.save()
            messages.success(request, "Financial year updated successfully.")
            return redirect("web_financial_years")
    else:
        form = FinancialYearForm(instance=financial_year)

    return render(request, "financial_years/edit.html", {
        "form": form,
        "financial_year": financial_year
    })

# Contribution Weeks
@login_required(login_url="login")
def contribution_week_list(request):
    weeks = ContributionWeek.objects.select_related(
        "church",
        "financial_year"
    ).all()

    return render(request, "contribution_weeks/list.html", {
        "weeks": weeks
    })

@login_required(login_url="login")
def contribution_week_create(request):
    if request.method == "POST":
        form = ContributionWeekForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Contribution week created successfully.")
            return redirect("web_contribution_weeks")
    else:
        form = ContributionWeekForm()

    return render(request, "contribution_weeks/create.html", {
        "form": form
    })

@login_required(login_url="login")
def contribution_week_edit(request, week_id):
    week = get_object_or_404(ContributionWeek, id=week_id)

    if request.method == "POST":
        form = ContributionWeekForm(request.POST, instance=week)

        if form.is_valid():
            form.save()
            messages.success(request, "Contribution week updated successfully.")
            return redirect("web_contribution_weeks")
    else:
        form = ContributionWeekForm(instance=week)

    return render(request, "contribution_weeks/edit.html", {
        "form": form,
        "week": week
    })

@login_required(login_url="login")
@require_POST
def contribution_week_activate(request, week_id):
    week = get_object_or_404(ContributionWeek, id=week_id)
    week.is_active = True
    week.is_closed = False
    week.save()

    messages.success(request, f"Week {week.week_number} activated successfully.")
    return redirect("web_contribution_weeks")

@login_required(login_url="login")
@require_POST
def contribution_week_close(request, week_id):
    week = get_object_or_404(ContributionWeek, id=week_id)
    week.is_closed = True
    week.is_active = False
    week.save()

    messages.success(request, f"Week {week.week_number} closed successfully.")
    return redirect("web_contribution_weeks")

@login_required(login_url="login")
def contribution_week_generate(request):
    if request.method == "POST":
        form = GenerateWeeksForm(request.POST)

        if form.is_valid():
            church = form.cleaned_data["church"]
            financial_year = form.cleaned_data["financial_year"]

            start_date = financial_year.start_date
            end_date = financial_year.end_date

            current_date = start_date

            while current_date.weekday() != 6:
                current_date += timedelta(days=1)

            week_number = 1
            created_count = 0

            while current_date <= end_date:
                week, created = ContributionWeek.objects.get_or_create(
                    church=church,
                    financial_year=financial_year,
                    week_number=week_number,
                    defaults={
                        "sunday_date": current_date,
                        "is_active": False,
                        "is_closed": False,
                    }
                )

                if created:
                    created_count += 1

                week_number += 1
                current_date += timedelta(days=7)

            messages.success(
                request,
                f"{created_count} contribution weeks generated successfully."
            )

            return redirect("web_contribution_weeks")
    else:
        form = GenerateWeeksForm()

    return render(request, "contribution_weeks/generate.html", {
        "form": form
    })

def annual_target_list(request):
    targets = MemberAnnualTarget.objects.select_related(
        "member",
        "member__user",
        "church",
        "financial_year",
        "category",
    ).all()

    return render(request, "annual_targets/list.html", {
        "targets": targets
    })

@login_required(login_url="login")
def annual_target_create(request):
    if request.method == "POST":
        form = MemberAnnualTargetForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Annual target created successfully.")
            return redirect("web_annual_targets")
    else:
        form = MemberAnnualTargetForm()

    return render(request, "annual_targets/create.html", {
        "form": form
    })

@login_required(login_url="login")
def annual_target_edit(request, target_id):
    target = get_object_or_404(MemberAnnualTarget, id=target_id)

    if request.method == "POST":
        form = MemberAnnualTargetForm(request.POST, instance=target)

        if form.is_valid():
            form.save()
            messages.success(request, "Annual target updated successfully.")
            return redirect("web_annual_targets")
    else:
        form = MemberAnnualTargetForm(instance=target)

    return render(request, "annual_targets/edit.html", {
        "form": form,
        "target": target
    })

#Contribution Management
@login_required(login_url="login")
def contribution_list(request):
    contributions = Contribution.objects.select_related(
        "church",
        "member",
        "member__user",
        "financial_year",
        "contribution_week",
        "category",
        "posted_by",
    ).all()

    return render(request, "contributions/list.html", {
        "contributions": contributions
    })

@login_required(login_url="login")
def contribution_create(request):
    if request.method == "POST":
        form = ContributionForm(request.POST)

        if form.is_valid():
            contribution = form.save(commit=False)

            if not contribution.reference_number:
                contribution.reference_number = f"MANUAL-{uuid.uuid4().hex[:10].upper()}"

            contribution.posted_by = request.user
            contribution.save()

            update_member_target(contribution)

            messages.success(request, "Contribution recorded successfully.")
            return redirect("web_contributions")
    else:
        form = ContributionForm()

    return render(request, "contributions/create.html", {
        "form": form
    })


@login_required(login_url="login")
def contribution_edit(request, contribution_id):
    contribution = get_object_or_404(Contribution, id=contribution_id)

    old_amount = contribution.amount
    old_category = contribution.category
    old_member = contribution.member
    old_year = contribution.financial_year

    if request.method == "POST":
        form = ContributionForm(request.POST, instance=contribution)

        if form.is_valid():
            updated_contribution = form.save()

            recalculate_member_targets(
                old_member,
                old_year,
                old_category
            )

            update_member_target(updated_contribution)

            messages.success(request, "Contribution updated successfully.")
            return redirect("web_contributions")
    else:
        form = ContributionForm(instance=contribution)

    return render(request, "contributions/edit.html", {
        "form": form,
        "contribution": contribution
    })

@login_required(login_url="login")
def update_member_target(contribution):
    target, created = MemberAnnualTarget.objects.get_or_create(
        member=contribution.member,
        church=contribution.church,
        financial_year=contribution.financial_year,
        category=contribution.category,
        defaults={
            "target_amount": 0,
            "contributed_amount": 0,
        }
    )

    target.contributed_amount += contribution.amount
    target.save()


@login_required(login_url="login")
def recalculate_member_targets(member, financial_year, category):
    target = MemberAnnualTarget.objects.filter(
        member=member,
        financial_year=financial_year,
        category=category,
    ).first()

    if target:
        total = Contribution.objects.filter(
            member=member,
            financial_year=financial_year,
            category=category,
            status="POSTED",
        ).exclude(status="REVERSED").aggregate(
            total=models.Sum("amount")
        )["total"] or 0

        target.contributed_amount = total
        target.save()

# Excel Uploads Management
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

    return render(request, "excel_uploads/list.html", {
        "uploads": uploads
    })

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

            messages.success(request, "Excel file uploaded and validated successfully.")
            return redirect("web_excel_upload_detail", upload_id=upload.id)
    else:
        form = ExcelUploadForm()

    return render(request, "excel_uploads/create.html", {
        "form": form
    })

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
        id=upload_id
    )

    rows = upload.rows.select_related("resolved_member").all()

    return render(request, "excel_uploads/detail.html", {
        "upload": upload,
        "rows": rows
    })

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
        description=f"Approved Excel upload {upload.upload_reference}.",
        entity_type="ExcelUpload",
        entity_id=upload.id,
        request=request,
    )

    messages.success(request, "Upload approved and contributions posted successfully.")
    return redirect("web_excel_upload_detail", upload_id=upload.id)


# Reports and Analytics Views would go here
@login_required(login_url="login")
def contribution_summary_report(request):
    church_id = request.GET.get("church")
    financial_year_id = request.GET.get("financial_year")
    category_id = request.GET.get("category")

    targets = MemberAnnualTarget.objects.select_related(
        "member",
        "member__user",
        "church",
        "financial_year",
        "category",
    ).all()

    if church_id:
        targets = targets.filter(church_id=church_id)

    if financial_year_id:
        targets = targets.filter(financial_year_id=financial_year_id)

    if category_id:
        targets = targets.filter(category_id=category_id)

    summary = list(
        targets.values(
            "category__name"
        ).annotate(
            total_target=Sum("target_amount"),
            total_contributed=Sum("contributed_amount"),
            total_remaining=Sum("remaining_amount"),
        ).order_by("category__name")
    )

    for item in summary:
        total_target = item["total_target"] or 0
        total_contributed = item["total_contributed"] or 0

        if total_target > 0:
            item["completion_percentage"] = round(
                (total_contributed / total_target) * 100,
                2
            )
        else:
            item["completion_percentage"] = 0

    churches = Church.objects.filter(is_active=True)
    financial_years = FinancialYear.objects.all()
    categories = ContributionCategory.objects.filter(is_active=True)

    return render(request, "reports/contribution_summary.html", {
        "summary": summary,
        "churches": churches,
        "financial_years": financial_years,
        "categories": categories,
        "selected_church": church_id,
        "selected_financial_year": financial_year_id,
        "selected_category": category_id,
    })


# Member Statements, Contribution Trends, and other report views would be implemented similarly, using appropriate queries and templates to display the data.
@login_required(login_url="login")
def member_statement_report(request):
    member_id = request.GET.get("member")

    members = Member.objects.select_related(
        "user",
        "church",
        "jumuiya"
    ).all()

    selected_member = None
    targets = []
    contributions = []
    total_contributed = 0

    if member_id:
        selected_member = get_object_or_404(
            Member.objects.select_related(
                "user",
                "church",
                "jumuiya"
            ),
            id=member_id
        )

        targets = MemberAnnualTarget.objects.filter(
            member=selected_member
        ).select_related(
            "category",
            "financial_year"
        )

        contributions = Contribution.objects.filter(
            member=selected_member,
            status="POSTED"
        ).select_related(
            "category",
            "contribution_week",
            "financial_year"
        ).order_by(
            "-contribution_date"
        )

        total_contributed = contributions.aggregate(
            total=models.Sum("amount")
        )["total"] or 0

    return render(request, "reports/member_statement.html", {
        "members": members,
        "selected_member": selected_member,
        "targets": targets,
        "contributions": contributions,
        "total_contributed": total_contributed,
        "selected_member_id": member_id,
    })


#Weekly collection report
@login_required(login_url="login")
def weekly_collection_report(request):
    week_id = request.GET.get("week")

    weeks = ContributionWeek.objects.select_related(
        "church",
        "financial_year"
    ).order_by("-sunday_date")

    selected_week = None
    summary = []
    grand_total = 0

    if week_id:
        selected_week = get_object_or_404(ContributionWeek, id=week_id)

        summary = Contribution.objects.filter(
            contribution_week=selected_week,
            status="POSTED"
        ).values(
            "category__name"
        ).annotate(
            total_amount=Sum("amount")
        ).order_by(
            "category__name"
        )

        grand_total = Contribution.objects.filter(
            contribution_week=selected_week,
            status="POSTED"
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

    return render(request, "reports/weekly_collection.html", {
        "weeks": weeks,
        "selected_week": selected_week,
        "summary": summary,
        "grand_total": grand_total,
        "selected_week_id": week_id,
    })

#Jumuiya Management
@login_required(login_url="login")
def jumuiya_list(request):
    jumuiya_list = Jumuiya.objects.select_related("church").all()

    return render(request, "jumuiya/list.html", {
        "jumuiya_list": jumuiya_list
    })

@login_required(login_url="login")
def jumuiya_create(request):
    if request.method == "POST":
        form = JumuiyaForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Jumuiya created successfully.")
            return redirect("web_jumuiya")
    else:
        form = JumuiyaForm()

    return render(request, "jumuiya/create.html", {
        "form": form
    })

@login_required(login_url="login")
def jumuiya_edit(request, jumuiya_id):
    jumuiya = get_object_or_404(Jumuiya, id=jumuiya_id)

    if request.method == "POST":
        form = JumuiyaForm(request.POST, instance=jumuiya)

        if form.is_valid():
            form.save()
            messages.success(request, "Jumuiya updated successfully.")
            return redirect("web_jumuiya")
    else:
        form = JumuiyaForm(instance=jumuiya)

    return render(request, "jumuiya/edit.html", {
        "form": form,
        "jumuiya": jumuiya
    })

    # User Access Control Views
@login_required(login_url="login")
@require_POST
def user_activate(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()

    messages.success(
        request,
        f"{user.full_name} activated successfully."
    )

    return redirect("web_users")

@login_required(login_url="login")
@require_POST
def user_deactivate(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.error(
            request,
            "You cannot deactivate your own account."
        )
        return redirect("web_users")

    user.is_active = False
    user.save()

    messages.success(
        request,
        f"{user.full_name} deactivated successfully."
    )

    return redirect("web_users")

# Church Management
@login_required(login_url="login")
def church_list(request):
    churches = Church.objects.all().order_by("church_name")

    return render(request, "churches/list.html", {
        "churches": churches
    })

@login_required(login_url="login")
def church_create(request):
    if request.method == "POST":
        form = ChurchForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Church created successfully.")
            return redirect("web_churches")
    else:
        form = ChurchForm()

    return render(request, "churches/create.html", {
        "form": form
    })

@login_required(login_url="login")
def church_edit(request, church_id):
    church = get_object_or_404(Church, id=church_id)

    if request.method == "POST":
        form = ChurchForm(request.POST, instance=church)

        if form.is_valid():
            form.save()
            messages.success(request, "Church updated successfully.")
            return redirect("web_churches")
    else:
        form = ChurchForm(instance=church)

    return render(request, "churches/edit.html", {
        "form": form,
        "church": church
    })

# Audit Logs View
@login_required(login_url="login")
def audit_log_list(request):
    logs = AuditLog.objects.select_related(
        "user",
        "church"
    ).all()

    return render(request, "audit_logs/list.html", {
        "logs": logs
    })

# Notifications View
@login_required(login_url="login")
def notification_list(request):
    notifications = Notification.objects.select_related(
        "church",
        "created_by",
    ).all()

    return render(request, "notifications/list.html", {
        "notifications": notifications
    })

@login_required(login_url="login")
def notification_create(request):
    if request.method == "POST":
        form = NotificationForm(request.POST)

        if form.is_valid():
            notification = form.save(commit=False)
            notification.created_by = request.user
            notification.status = "SENT"
            notification.sent_at = timezone.now()
            notification.save()

            create_audit_log(
                user=request.user,
                church=notification.church,
                action="OTHER",
                description=f"Sent notification: {notification.title}",
                entity_type="Notification",
                entity_id=notification.id,
                request=request,
            )

            messages.success(request, "Notification sent successfully.")
            return redirect("web_notifications")
    else:
        form = NotificationForm()

    return render(request, "notifications/create.html", {
        "form": form
    })

# Profile and Password Management
@login_required(login_url="login")
def profile_view(request):
    if request.method == "POST":
        form = ProfileUpdateForm(
            request.POST,
            instance=request.user
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("web_profile")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "profile/detail.html", {
        "form": form
    })


@login_required(login_url="login")
def change_password_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(
            request.user,
            request.POST
        )

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            messages.success(request, "Password changed successfully.")
            return redirect("web_profile")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "profile/change_password.html", {
        "form": form
    })
