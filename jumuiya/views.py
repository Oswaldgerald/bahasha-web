from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render

from jumuiya.models import Jumuiya
from web.forms import JumuiyaForm
from web.pagination import paginate_queryset


@login_required(login_url="login")
def jumuiya_list(request):
    jumuiya_list = Jumuiya.objects.select_related("church").order_by(
        "church__church_name", "name"
    )
    jumuiya_list = paginate_queryset(request, jumuiya_list)

    return render(request, "jumuiya/list.html", {"jumuiya_list": jumuiya_list})


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

    return render(request, "jumuiya/create.html", {"form": form})


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

    return render(request, "jumuiya/edit.html", {"form": form, "jumuiya": jumuiya})
