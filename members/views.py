from .models import Member

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.views.decorators.http import require_POST

from annual_targets.models import MemberAnnualTarget
from audit_logs.services import create_audit_log
from contributions.models import Contribution
from jumuiya.models import Jumuiya
from members.services import (
    approve_member as approve_member_record,
    reject_member as reject_member_record,
)
from web.forms import MemberCreateForm
from web.forms import MemberEditForm


@login_required(login_url="login")
def member_card(request, member_id):
    member = get_object_or_404(
        Member.objects.select_related("user", "church", "jumuiya"), id=member_id
    )

    return render(request, "members/card.html", {"member": member})


@login_required(login_url="login")
def member_list(request):
    members = Member.objects.select_related("user", "church", "jumuiya")
    if request.user.church_id and not request.user.is_superuser:
        members = members.filter(church_id=request.user.church_id)

    summary = members.aggregate(
        total=models.Count("id"),
        approved=models.Count("id", filter=models.Q(approval_status="APPROVED")),
        pending=models.Count("id", filter=models.Q(approval_status="PENDING")),
        inactive=models.Count("id", filter=models.Q(is_active=False)),
    )

    query = request.GET.get("q", "").strip()
    approval_status = request.GET.get("approval_status", "").strip()
    activity_status = request.GET.get("activity_status", "").strip()

    if query:
        members = members.filter(
            models.Q(user__full_name__icontains=query)
            | models.Q(user__phone_number__icontains=query)
            | models.Q(user__username__icontains=query)
            | models.Q(bahasha_number__icontains=query)
        )
    if approval_status in dict(Member.APPROVAL_STATUS):
        members = members.filter(approval_status=approval_status)
    if activity_status == "active":
        members = members.filter(is_active=True)
    elif activity_status == "inactive":
        members = members.filter(is_active=False)

    paginator = Paginator(members, 25)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "members/member_list.html",
        {
            "members": page,
            "summary": summary,
            "filters": {
                "q": query,
                "approval_status": approval_status,
                "activity_status": activity_status,
            },
        },
    )


def member_queryset_for_user(user):
    queryset = Member.objects.select_related("user", "church", "jumuiya")
    if user.church_id and not user.is_superuser:
        queryset = queryset.filter(church_id=user.church_id)
    return queryset


@login_required(login_url="login")
def member_jumuiya_options(request):
    church_id = request.GET.get("church_id")
    if not church_id or not church_id.isdigit():
        return JsonResponse({"options": []})

    jumuiya = Jumuiya.objects.filter(church_id=church_id, is_active=True)
    if request.user.church_id and not request.user.is_superuser:
        jumuiya = jumuiya.filter(church_id=request.user.church_id)

    return JsonResponse(
        {
            "options": [
                {"value": item.id, "label": item.name}
                for item in jumuiya.order_by("name")
            ]
        }
    )


@login_required(login_url="login")
@require_POST
def approve_member(request, member_id):
    member = get_object_or_404(member_queryset_for_user(request.user), id=member_id)
    approve_member_record(member)
    create_audit_log(
        user=request.user,
        church=member.church,
        action="MEMBER_APPROVED",
        description=f"Approved member {member.user.full_name}.",
        entity_type="Member",
        entity_id=member.id,
        request=request,
    )

    messages.success(request, f"{member.user.full_name} approved successfully.")

    return redirect("web_members")


@login_required(login_url="login")
@require_POST
def reject_member(request, member_id):
    member = get_object_or_404(member_queryset_for_user(request.user), id=member_id)
    reject_member_record(member)
    create_audit_log(
        user=request.user,
        church=member.church,
        action="MEMBER_REJECTED",
        description=f"Rejected member {member.user.full_name}.",
        entity_type="Member",
        entity_id=member.id,
        request=request,
    )

    messages.success(request, f"{member.user.full_name} rejected.")

    return redirect("web_members")


@login_required(login_url="login")
def member_detail(request, member_id):
    member = get_object_or_404(member_queryset_for_user(request.user), id=member_id)

    targets = MemberAnnualTarget.objects.filter(member=member).select_related(
        "category", "financial_year"
    )

    posted_contributions = Contribution.objects.filter(
        member=member,
        status="POSTED",
    ).select_related("category", "contribution_week")

    total_contributed = (
        posted_contributions.aggregate(total=models.Sum("amount"))["total"] or 0
    )
    contribution_count = posted_contributions.count()
    target_summary = targets.aggregate(
        total=models.Sum("target_amount"),
        contributed=models.Sum("contributed_amount"),
        remaining=models.Sum("remaining_amount"),
    )
    contributions = posted_contributions.order_by("-contribution_date", "-created_at")[
        :20
    ]

    context = {
        "member": member,
        "targets": targets,
        "contributions": contributions,
        "contribution_count": contribution_count,
        "total_contributed": total_contributed,
        "target_summary": target_summary,
    }

    return render(request, "members/member_detail.html", context)


@login_required(login_url="login")
def member_create(request):
    if request.method == "POST":
        form = MemberCreateForm(request.POST, request_user=request.user)

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
        form = MemberCreateForm(request_user=request.user)

    return render(request, "members/create.html", {"form": form})


@login_required(login_url="login")
def member_edit(request, member_id):
    member = get_object_or_404(member_queryset_for_user(request.user), id=member_id)

    if request.method == "POST":
        form = MemberEditForm(request.POST, member=member, request_user=request.user)

        if form.is_valid():
            member = form.save()
            create_audit_log(
                user=request.user,
                church=member.church,
                action="MEMBER_UPDATED",
                description=f"Updated member {member.user.full_name}.",
                entity_type="Member",
                entity_id=member.id,
                request=request,
            )
            messages.success(request, "Member updated successfully.")
            return redirect("web_members")
    else:
        form = MemberEditForm(member=member, request_user=request.user)

    return render(request, "members/edit.html", {"form": form, "member": member})
