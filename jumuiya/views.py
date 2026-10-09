from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render

from jumuiya.models import Jumuiya
from web.forms import JumuiyaForm
from web.pagination import paginate_queryset
from web.access import member_management_required, scope_queryset_to_church


@member_management_required
def jumuiya_list(request):
    jumuiya_list = Jumuiya.objects.select_related("church").order_by(
        "church__church_name", "name"
    )
    jumuiya_list = scope_queryset_to_church(jumuiya_list, request.user)
    jumuiya_list = paginate_queryset(request, jumuiya_list)

    return render(request, "jumuiya/list.html", {"jumuiya_list": jumuiya_list})


@member_management_required
def jumuiya_create(request):
    if request.method == "POST":
        form = JumuiyaForm(request.POST, request_user=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Jumuiya created successfully.")
            return redirect("web_jumuiya")
    else:
        form = JumuiyaForm(request_user=request.user)

    return render(request, "jumuiya/create.html", {"form": form})


@member_management_required
def jumuiya_edit(request, jumuiya_id):
    jumuiya = get_object_or_404(
        scope_queryset_to_church(Jumuiya.objects.all(), request.user),
        id=jumuiya_id,
    )

    if request.method == "POST":
        form = JumuiyaForm(
            request.POST, instance=jumuiya, request_user=request.user
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Jumuiya updated successfully.")
            return redirect("web_jumuiya")
    else:
        form = JumuiyaForm(instance=jumuiya, request_user=request.user)

    return render(request, "jumuiya/edit.html", {"form": form, "jumuiya": jumuiya})
